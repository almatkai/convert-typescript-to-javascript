#!/usr/bin/env python3
import json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[2]
cases=json.loads((r/'v2/tests/locked-source-flow.json').read_text())
a=subprocess.run(['node',str(r/'v2/tools/oracle.cjs')],cwd=r/'v2/.qa/v1',input=''.join(json.dumps({k:v for k,v in c.items() if k!='expected'})+'\n' for c in cases),text=True,capture_output=True,check=True)
actual=list(map(json.loads,a.stdout.strip().split('\n')))
assert actual==[c['expected'] for c in cases]
print(json.dumps({'lockedSourceFlowCases':len(cases),'transformedProgramsExecuted':0}))
