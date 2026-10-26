#!/usr/bin/env python3
"""Deterministic closed-inventory development ZIP, never publish or install."""
import argparse,hashlib,json,os,pathlib,stat,zipfile
r=pathlib.Path(__file__).resolve().parents[2];v=r/'v2'
p=argparse.ArgumentParser();p.add_argument('--binary',default=str(v/'target/release/tezbar-convert-typescript-to-javascript'));args=p.parse_args()
binary=pathlib.Path(args.binary);assert binary.is_file()
files={'bin/tezbar-convert-typescript-to-javascript':binary.read_bytes(),'resources/icon.png':(v/'resources/icon.png').read_bytes(),'LICENSE':(v/'LICENSE').read_bytes(),'NOTICE':(v/'NOTICE').read_bytes()}
for f in sorted((v/'licenses').rglob('*')):
 if f.is_file():files[f.relative_to(v).as_posix()]=f.read_bytes()
manifest=json.loads((v/'extension.json').read_text());assert manifest['artifacts']=={}
manifest['files']={name:hashlib.sha256(b).hexdigest() for name,b in sorted(files.items())}
files['extension.json']=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
dist=v/'dist';dist.mkdir(exist_ok=True);out=dist/'convert-typescript-to-javascript-2.0.0-aarch64-apple-darwin-development.zip'
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name,b in sorted(files.items()):
  info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(stat.S_IFREG | (0o755 if name.startswith('bin/') else 0o644))<<16;z.writestr(info,b,compresslevel=9)
with zipfile.ZipFile(out) as z:
 assert len(z.namelist())==len(set(z.namelist()))
 assert set(z.namelist())==set(manifest['files'])|{'extension.json'}
 for name,digest in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
 target=dist/'extracted'
 for name in z.namelist():
  assert not name.startswith('/') and '..' not in pathlib.PurePosixPath(name).parts
  f=target/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(z.read(name));f.chmod(0o755 if name.startswith('bin/') else 0o644)
record={'archive':out.name,'archiveSha256':hashlib.sha256(out.read_bytes()).hexdigest(),'executableSha256':manifest['files']['bin/tezbar-convert-typescript-to-javascript'],'members':len(files),'status':'development review candidate; not installed or published'}
(dist/'package.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
