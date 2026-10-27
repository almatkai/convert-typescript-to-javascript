#!/usr/bin/env python3
"""Parse/transform only. Never execute generated user JavaScript."""
import argparse,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--record',action='store_true');p.add_argument('--binary',default=str(root/'v2/target/debug/examples/transform'));args=p.parse_args()
cases=json.loads((root/'v2/tests/compiler-cases.json').read_text())
a=subprocess.run([args.binary],input=''.join(json.dumps(c['source'])+'\n' for c in cases),text=True,capture_output=True,check=True)
b=subprocess.run(['node',str(root/'v2/tools/oracle.cjs')],input=''.join(json.dumps(c)+'\n' for c in cases),text=True,capture_output=True,cwd=root/'v2/.qa/v1',check=True)
n=list(map(json.loads,a.stdout.rstrip('\n').split('\n')));o=list(map(json.loads,b.stdout.rstrip('\n').split('\n')));assert len(n)==len(o)==len(cases)
report=[];locked=[]
for c,native,babel in zip(cases,n,o):
 babel.pop('flow',None);report.append(dict(c,native=native,babel=babel,exact=native==babel));locked.append(dict(c,expected=babel))
if args.record:(root/'v2/tests/locked-babel.json').write_text(json.dumps(locked,ensure_ascii=False,indent=2)+'\n')
else:assert locked==json.loads((root/'v2/tests/locked-babel.json').read_text()),'Locked Babel fixtures drifted'
(root/'v2/.qa/compiler-differential.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
failed=[r for r in report if not r['exact']]
print(f"Exact Babel parity: {len(report)-len(failed)}/{len(report)}")
for r in failed:print(r['name'],json.dumps(r['native'],ensure_ascii=False),json.dumps(r['babel'],ensure_ascii=False))
sys.exit(bool(failed))
