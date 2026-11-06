import http.client
import io
import os
from email.message import Message
import json
from pathlib import Path
import tempfile
import threading
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class PortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['DEVSPACE_INITIAL_PASSWORD']='test-only-password'
        cls.tmp=tempfile.TemporaryDirectory(); server.DATA=Path(cls.tmp.name); server.initialize()
        if os.environ.get('DEVSPACE_TEST_IN_MEMORY') == '1': return
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=cls.http.serve_forever,daemon=True).start(); cls.port=cls.http.server_port
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'http'): cls.http.shutdown(); cls.http.server_close()
        cls.tmp.cleanup()
    def request(self,path,method='GET',body=None,cookie='',csrf='',headers=None):
        data=json.dumps(body).encode() if isinstance(body,dict) else body
        if os.environ.get('DEVSPACE_TEST_IN_MEMORY') == '1':
            handler=server.Handler.__new__(server.Handler);handler.path=path;handler.client_address=('127.0.0.1',1234)
            handler.connection=type('Connection',(),{'settimeout':lambda *_:None})()
            handler.headers=Message()
            for k,v in {'Content-Type':'application/json','Cookie':cookie,'X-CSRF-Token':csrf,**(headers or {}),'Content-Length':str(len(data or b''))}.items(): handler.headers[k]=v
            handler.rfile=io.BytesIO(data or b'');handler.wfile=io.BytesIO();result={'headers':{}}
            handler.send_response=lambda status:result.update(status=status)
            handler.send_header=lambda k,v:result['headers'].update({k:v})
            handler.end_headers=lambda:None
            handler.dispatch(method)
            return result['status'],result['headers'],handler.wfile.getvalue()
        con=http.client.HTTPConnection('127.0.0.1',self.port)
        con.request(method,path,data,{'Content-Type':'application/json','Cookie':cookie,'X-CSRF-Token':csrf,**(headers or {})})
        response=con.getresponse(); raw=response.read(); result=(response.status,dict(response.getheaders()),raw); con.close(); return result
    def login(self,name='hellodev',password='test-only-password',register=False):
        status,headers,data=self.request('/api/register' if register else '/api/login','POST',{'username':name,'password':password})
        self.assertEqual(status,200,data); return headers['Set-Cookie'].split(';')[0],json.loads(data)['csrf']
    def test_full_flow_and_isolation(self):
        self.assertEqual(self.request('/api/files')[0],401)
        cookie,csrf=self.login()
        status,_,body=self.request('/api/me',cookie=cookie); self.assertEqual(json.loads(body)['user']['role'],'developer')
        with server.db() as con:
            stored=con.execute('SELECT password FROM users WHERE username="hellodev"').fetchone()[0]
            self.assertNotEqual(stored,'test-only-password'); self.assertTrue(server.verify('test-only-password',stored))
        self.assertEqual(self.request('/api/profile','POST',{'name':'No'},cookie=cookie)[0],403)
        self.assertEqual(self.request('/api/files','POST',b'hello world',cookie,csrf,{'X-Filename':'../hello.txt','Content-Type':'application/octet-stream'})[0],201)
        files=json.loads(self.request('/api/files',cookie=cookie)[2])['files']; self.assertEqual(len(files),1); self.assertEqual(files[0]['name'],'hello.txt'); ident=files[0]['id']
        other,other_csrf=self.login('otheruser','password123',True)
        self.assertEqual(self.request('/api/files/'+ident,cookie=other)[0],404)
        self.assertEqual(self.request('/api/files/'+ident,'DELETE',cookie=other,csrf=other_csrf)[0],404)
        self.assertEqual(self.request('/api/files/'+ident,cookie=cookie)[2],b'hello world')
        self.assertEqual(self.request('/api/profile','POST',{'name':'Hello Dev','bio':'<script>alert(1)</script>','skills':'Python'},cookie,csrf)[0],200)
        profiles=json.loads(self.request('/api/profiles',cookie=cookie)[2])['profiles']; self.assertEqual(len(profiles),2); self.assertNotIn('password',profiles[0])
        self.assertEqual(self.request('/api/files/'+ident,'DELETE',cookie=cookie,csrf=csrf)[0],200)
        self.assertEqual(self.request('/api/logout','POST',{},cookie,csrf)[0],200)
        self.assertEqual(self.request('/api/files',cookie=cookie)[0],401)
    def test_login_rejects_wrong_password(self):
        self.assertEqual(self.request('/api/login','POST',{'username':'hellodev','password':'wrong12345'})[0],401)
    def test_size_limit_and_static(self):
        cookie,csrf=self.login()
        self.assertEqual(self.request('/api/files','POST',b'',cookie,csrf)[0],413)
        status,headers,body=self.request('/');self.assertEqual(status,200);self.assertIn(b'DevSpace',body);self.assertIn('Content-Security-Policy',headers)
        self.assertEqual(self.request('/data/portal.sqlite')[0],404)
        self.assertEqual(self.request('/static/../server.py')[0],404)

if __name__=='__main__': unittest.main()
