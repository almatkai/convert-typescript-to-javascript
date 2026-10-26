#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[2];assert pathlib.Path.cwd().resolve()==r
pin=json.loads((r/'v2/evidence/source/PIN.json').read_text())
for name,digest in pin['files'].items():
 b=(r/'v2/evidence/source'/name).read_bytes();assert hashlib.sha256(b).hexdigest()==digest
 p=r/'v2/.qa/v1'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
subprocess.run(['npm','ci','--prefix',str(r/'v2/.qa/v1'),'--ignore-scripts','--no-audit','--no-fund'],check=True)
