"""Create exactly 2.2 decimal GB of ZIP bytes, split below GitHub's asset limit.
The extra bytes are explicitly labeled padding, not website functionality.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=['server.py','README.md','start.bat','start.sh','static/index.html','static/style.css','static/app.js']
PADDING=['download-size-padding/part-%d.bin'%n for n in range(1,4)]

def write_zip(destination,target):
    skeleton=io.BytesIO()
    with zipfile.ZipFile(skeleton,'w',compression=zipfile.ZIP_STORED) as z:
        for name in FILES: z.writestr('DevSpace/'+name,(ROOT/name).read_bytes())
        for name in PADDING: z.writestr('DevSpace/'+name,b'')
    # ZIP64 adds a 56-byte end record and a 20-byte locator when central
    # directory offset exceeds Python zipfile's conservative 2 GiB limit.
    overhead=len(skeleton.getvalue())+(76 if target>zipfile.ZIP64_LIMIT+65536 else 0)
    remaining=target-overhead
    if remaining<0: raise ValueError('Target is smaller than the application')
    blocks=[remaining//3,remaining//3,remaining-2*(remaining//3)]
    zero=b'\0'*(1024*1024)
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED) as z:
        for name in FILES: z.write(ROOT/name,'DevSpace/'+name)
        for name,size in zip(PADDING,blocks):
            info=zipfile.ZipInfo('DevSpace/'+name); info.file_size=size
            with z.open(info,'w') as out:
                while size:
                    count=min(size,len(zero)); out.write(zero[:count]);size-=count
    if destination.stat().st_size!=target: raise RuntimeError('Archive size did not match requested byte count')
    with zipfile.ZipFile(destination) as z:
        if z.testzip(): raise RuntimeError('Archive integrity failed')

def package(target=2_200_000_000):
    out=ROOT/'dist';out.mkdir(exist_ok=True);archive=out/'DevSpace.zip'
    write_zip(archive,target)
    manifest={}
    with archive.open('rb') as source:
        for index,length in enumerate([target//2,target-target//2],1):
            name=f'DevSpace.zip.part{index}';digest=hashlib.sha256()
            with (out/name).open('wb') as output:
                while length:
                    data=source.read(min(length,1024*1024))
                    if not data: raise RuntimeError('Incomplete split')
                    output.write(data);digest.update(data);length-=len(data)
            manifest[name]={'bytes':(out/name).stat().st_size,'sha256':digest.hexdigest()}
    (out/'SHA256.json').write_text(json.dumps(manifest,indent=2))
    archive.unlink()
    print(json.dumps(manifest,indent=2))

if __name__=='__main__': package(int(sys.argv[1]) if len(sys.argv)>1 else 2_200_000_000)
