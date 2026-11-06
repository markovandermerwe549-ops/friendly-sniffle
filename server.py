"""DevSpace: dependency-free, local-first authenticated file portal."""
import hashlib
import hmac
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DEVSPACE_DATA', ROOT / 'data')).resolve()
MAX_UPLOAD = 100 * 1024 * 1024
QUOTA = 5 * 1024**3
LOCK = threading.Lock()
ATTEMPTS = {}

def db():
    con = sqlite3.connect(DATA / 'portal.sqlite', timeout=30)
    con.row_factory = sqlite3.Row
    return con

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()

def verify(password, stored):
    return hmac.compare_digest(password_hash(password, stored.split(':')[0]), stored)

def initialize():
    (DATA / 'uploads').mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'member', name TEXT NOT NULL, bio TEXT NOT NULL DEFAULT '', skills TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, csrf TEXT NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL, size INTEGER NOT NULL, created REAL NOT NULL);''')
        if not con.execute('SELECT 1 FROM users WHERE username=?', ('hellodev',)).fetchone():
            initial = os.environ.get('DEVSPACE_INITIAL_PASSWORD')
            if not initial:
                import getpass
                initial = getpass.getpass('First launch: set a private password for hellodev (8+ characters): ')
                if initial != getpass.getpass('Confirm password: '):
                    raise ValueError('Passwords did not match')
            if not 8 <= len(initial) <= 128:
                raise ValueError('Developer password must be 8–128 characters')
            con.execute('INSERT INTO users(username,password,role,name,bio,skills) VALUES(?,?,?,?,?,?)', ('hellodev', password_hash(initial), 'developer', 'Hello Developer', 'Building useful things. Welcome to my developer workspace.', 'Python, Web development'))

class Error(Exception):
    def __init__(self, status, message): self.status, self.message = status, message

class Handler(BaseHTTPRequestHandler):
    server_version = 'DevSpace/1.0'
    def log_message(self, *_): pass  # Do not log login bodies or session tokens.
    def send(self, status, body, content_type='application/json', headers=None):
        if not isinstance(body, bytes): body=json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'")
        for key, value in (headers or {}).items(): self.send_header(key,value)
        self.end_headers(); self.wfile.write(body)
    def json_body(self):
        try: size=int(self.headers.get('Content-Length','0'))
        except ValueError: raise Error(400,'Invalid request length')
        if not 0 < size <= 16384: raise Error(413,'Request too large')
        try:
            value=json.loads(self.rfile.read(size))
            if not isinstance(value,dict): raise ValueError()
            return value
        except (ValueError,UnicodeError): raise Error(400,'Invalid JSON')
    def session(self, required=True):
        cookie=SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception: pass
        token=cookie.get('session')
        with db() as con:
            row=con.execute('SELECT users.*,sessions.csrf,sessions.token FROM sessions JOIN users ON users.id=sessions.user_id WHERE token=? AND expires>?', (hashlib.sha256(token.value.encode()).hexdigest() if token else '',time.time())).fetchone()
        if required and not row: raise Error(401,'Please sign in')
        return row
    def protect(self):
        user=self.session()
        if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),user['csrf']): raise Error(403,'Invalid form token; refresh and try again')
        return user
    def public(self,user): return {k:user[k] for k in ['id','username','role','name','bio','skills']}
    def do_GET(self): self.dispatch('GET')
    def do_POST(self): self.dispatch('POST')
    def do_DELETE(self): self.dispatch('DELETE')
    def dispatch(self, method):
        self.connection.settimeout(60)
        try: self.route(method,self.path.split('?')[0])
        except Error as e: self.send(e.status,{'error':e.message})
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception: self.send(500,{'error':'Server error'})
    def route(self,method,path):
        if method=='GET' and path in ['/', '/static/app.js','/static/style.css']:
            file=ROOT/'static'/('index.html' if path=='/' else path.rsplit('/',1)[-1])
            return self.send(200,file.read_bytes(),mimetypes.guess_type(file)[0] or 'application/octet-stream')
        if method=='GET' and path=='/api/me':
            user=self.session(False)
            return self.send(200,{'user':self.public(user) if user else None,'csrf':user['csrf'] if user else None})
        if method=='POST' and path in ['/api/login','/api/register']:
            # JSON-only requests prevent cross-origin HTML form submissions.
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise Error(415,'Use JSON')
            body=self.json_body(); username=str(body.get('username','')).lower().strip(); password=str(body.get('password',''))
            ip=self.client_address[0]
            with LOCK:
                now=time.time(); recent=[t for t in ATTEMPTS.get(ip,[]) if t>now-300]
                if len(recent)>=15: raise Error(429,'Too many attempts; wait five minutes')
                ATTEMPTS[ip]=recent+[now]
            if not re.fullmatch(r'[a-z0-9_]{3,30}',username) or not 8<=len(password)<=128: raise Error(400,'Use a 3–30 character username and an 8–128 character password')
            with db() as con:
                if path=='/api/register':
                    try: con.execute('INSERT INTO users(username,password,name) VALUES(?,?,?)',(username,password_hash(password),username))
                    except sqlite3.IntegrityError: raise Error(409,'Username already taken')
                user=con.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
                if not user or not verify(password,user['password']): raise Error(401,'Incorrect username or password')
                token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(32)
                con.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
                con.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],csrf,time.time()+86400))
            cookie='session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400'
            if os.environ.get('DEVSPACE_HTTPS')=='1': cookie+='; Secure'
            return self.send(200,{'user':self.public(user),'csrf':csrf},headers={'Set-Cookie':cookie})
        if method=='POST' and path=='/api/logout':
            user=self.protect()
            with db() as con: con.execute('DELETE FROM sessions WHERE token=?',(user['token'],))
            return self.send(200,{'ok':True},headers={'Set-Cookie':'session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
        if method=='GET' and path=='/api/profiles':
            self.session()
            with db() as con: rows=con.execute('SELECT * FROM users ORDER BY role,username LIMIT 200').fetchall()
            return self.send(200,{'profiles':[self.public(u) for u in rows]})
        if method=='POST' and path=='/api/profile':
            user=self.protect(); body=self.json_body()
            values=[str(body.get(k,'')).strip() for k in ['name','bio','skills']]
            if not values[0] or len(values[0])>80 or len(values[1])>1000 or len(values[2])>200: raise Error(400,'Profile fields are missing or too long')
            with db() as con: con.execute('UPDATE users SET name=?,bio=?,skills=? WHERE id=?',(*values,user['id']))
            return self.send(200,{'ok':True})
        if method=='GET' and path=='/api/files':
            user=self.session()
            with db() as con: rows=con.execute('SELECT id,name,size,created FROM files WHERE user_id=? ORDER BY created DESC',(user['id'],)).fetchall()
            return self.send(200,{'files':[dict(f) for f in rows],'maxUpload':MAX_UPLOAD})
        if method=='POST' and path=='/api/files':
            user=self.protect()
            try: size=int(self.headers.get('Content-Length','0'))
            except ValueError: raise Error(400,'Invalid file length')
            if not 0<size<=MAX_UPLOAD: raise Error(413,'Files must be between 1 byte and 100 MiB')
            from urllib.parse import unquote
            name=unquote(self.headers.get('X-Filename','upload.bin')).replace('\\','/').rsplit('/',1)[-1]
            name=''.join(c for c in name if ord(c)>=32 and ord(c)!=127)[:180] or 'upload.bin'
            ident=secrets.token_hex(16); destination=DATA/'uploads'/ident
            # Serialize reservations so concurrent uploads cannot bypass total quota.
            with LOCK:
                with db() as con:
                    used=con.execute('SELECT COALESCE(SUM(size),0) FROM files').fetchone()[0]
                    if used+size>QUOTA: raise Error(413,'Server storage limit reached')
                    con.execute('INSERT INTO files VALUES(?,?,?,?,?)',(ident,user['id'],name,size,time.time()))
            try:
                with destination.open('xb') as out:
                    remaining=size
                    while remaining:
                        chunk=self.rfile.read(min(1024*1024,remaining))
                        if not chunk: raise Error(400,'Incomplete upload')
                        out.write(chunk); remaining-=len(chunk)
            except Exception:
                destination.unlink(missing_ok=True)
                with db() as con: con.execute('DELETE FROM files WHERE id=?',(ident,))
                raise
            return self.send(201,{'ok':True})
        if path.startswith('/api/files/') and method in ['GET','DELETE']:
            user=self.protect() if method=='DELETE' else self.session()
            ident=path.rsplit('/',1)[-1]
            with db() as con: file=con.execute('SELECT * FROM files WHERE id=? AND user_id=?',(ident,user['id'])).fetchone()
            if not file: raise Error(404,'File not found')
            destination=DATA/'uploads'/file['id']
            if method=='DELETE':
                destination.unlink(missing_ok=True)
                with db() as con: con.execute('DELETE FROM files WHERE id=?',(ident,))
                return self.send(200,{'ok':True})
            from urllib.parse import quote
            self.send_response(200); self.send_header('Content-Type','application/octet-stream'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(file['name'])); self.send_header('Content-Length',str(file['size'])); self.end_headers()
            with destination.open('rb') as stream:
                while chunk:=stream.read(1024*1024): self.wfile.write(chunk)
            return
        raise Error(404,'Not found')

if __name__=='__main__':
    initialize()
    host=os.environ.get('DEVSPACE_HOST','127.0.0.1'); port=int(os.environ.get('PORT','8080'))
    print(f'DevSpace running at http://{host}:{port}',flush=True)
    ThreadingHTTPServer((host,port),Handler).serve_forever()
