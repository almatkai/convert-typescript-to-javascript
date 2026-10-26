#!/usr/bin/env python3
"""Hash every Git-visible candidate file. Never stage, commit, push, or delete."""
import argparse,hashlib,pathlib,subprocess
from audit import audit,ROOT
p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');args=p.parse_args();audit()
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
paths=sorted(p for p in paths if p and (p.startswith('v2/') or p=='README.md') and p!='v2/INVENTORY.sha256')
text=''.join(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()+'  '+p+'\n' for p in paths)
file=ROOT/'v2/INVENTORY.sha256'
if args.write:file.write_text(text)
else:assert file.read_text()==text,'Candidate inventory drift; re-finalize before parent review'
print('Candidate files hashed:',len(paths),'inventorySha256:',hashlib.sha256(text.encode()).hexdigest())
