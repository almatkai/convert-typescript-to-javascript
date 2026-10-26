#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
def digest(data):return hashlib.sha256(data).hexdigest()
def audit():
 assert pathlib.Path.cwd().resolve()==ROOT
 assert subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip()==str(ROOT)
 assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='feat/native-v2-rust'
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='f80a47f6d462b29e71f9c282bce8e84bd6ef923e'
 assert not subprocess.check_output(['git','diff','--cached','--name-only'])
 pin=json.loads((ROOT/'v2/evidence/source/PIN.json').read_text());source_count=len(pin['files'])
 for name,sha in pin['files'].items():
  original=(ROOT/'v2/evidence/source'/name).read_bytes();assert digest(original)==sha
  actual=(ROOT/name).read_bytes()
  if name=='README.md':assert actual==original+b'\n\n[Native Rust v2 review candidate](v2/README.md).\n'
  else:assert actual==original,'V1 changed: '+name
 for label in ['host','sdk']:
  pin=json.loads((ROOT/'v2/evidence'/label/'PIN.json').read_text())
  for name,sha in pin['files'].items():assert digest((ROOT/'v2/evidence'/label/name).read_bytes())==sha
 baseline=json.loads((ROOT/'v2/evidence/ROUND2_BASELINE.json').read_text())
 for name,record in baseline['retainedOraclePrefixes'].items():
  values=json.loads((ROOT/'v2'/name).read_text());prefix=(json.dumps(values[:record['retainedOriginalCount']],ensure_ascii=False,indent=2)+'\n').encode();assert digest(prefix)==record['originalSerializedSha256'],'Original oracle prefix changed: '+name
 icon=json.loads((ROOT/'v2/evidence/icon.json').read_text());assert digest((ROOT/'v2/resources/icon.png').read_bytes())==icon['sha256']==icon['v1Sha256']
 license_records=json.loads((ROOT/'v2/licenses/dependencies.json').read_text())
 for record in license_records:
  assert record['licenseFiles'],'Missing licensing evidence: '+record['name']
  for name,sha in record['licenseFiles'].items():assert digest((ROOT/'v2/licenses/dependencies'/f"{record['name']}-{record['version']}"/name).read_bytes())==sha
 visible=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
 for name in filter(None,visible):
  assert not any(part in name.split('/') for part in ['target','node_modules','.qa','dist','__pycache__'])
  assert not name.endswith(('.pyc','.zip'))
 changes=subprocess.check_output(['git','diff','--name-only'],text=True).splitlines();assert changes==['README.md']
 print(json.dumps({'V1':'unchanged except exact README link','sourceFiles':source_count,'index':'empty','iconSha256':icon['sha256'],'dependencyLicensingRecords':len(license_records),'visibleFiles':len(list(filter(None,visible)))}))
if __name__=='__main__':audit()
