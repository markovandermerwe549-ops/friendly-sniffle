"""Put this script, both download parts, and SHA256.json together; run python unpack.py."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

root=Path(__file__).resolve().parent
manifest=json.loads((root/'SHA256.json').read_text())
archive=root/'DevSpace.zip'
try:
    with archive.open('wb') as output:
        for name in ['DevSpace.zip.part1','DevSpace.zip.part2']:
            digest=hashlib.sha256();size=0
            with (root/name).open('rb') as source:
                while chunk:=source.read(1024*1024):
                    output.write(chunk);digest.update(chunk);size+=len(chunk)
            if digest.hexdigest()!=manifest[name]['sha256'] or size!=manifest[name]['bytes']:
                raise ValueError('Download is incomplete or corrupted: '+name)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            # Padding provides the requested download size; it is not needed to run.
            path=Path(item.filename)
            if path.is_absolute() or '..' in path.parts: raise ValueError('Unsafe archive path')
            if 'download-size-padding' not in path.parts: z.extract(item,root)
    print('Ready! Open DevSpace/start.bat on Windows, or run python3 DevSpace/server.py.')
finally:
    archive.unlink(missing_ok=True)
