#!/usr/bin/env python3
"""Actual production SDK executable vs original command callbacks, owned pipes.
Every retained compiler case goes through both commands; no emitted JS is run.
"""
import argparse,json,os,pathlib,selectors,subprocess,time,uuid
r=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);args=p.parse_args()
cases=json.loads((r/'v2/tests/compiler-cases.json').read_text())
inputs=[dict(c,command=command) for command in ['copy','paste'] for c in cases]
a=subprocess.run(['node',str(r/'v2/tools/oracle.cjs')],cwd=r/'v2/.qa/v1',input=''.join(json.dumps(c)+'\n' for c in inputs),text=True,capture_output=True,check=True)
oracles=list(map(json.loads,a.stdout.rstrip('\n').split('\n')));assert len(oracles)==len(inputs)
proc=subprocess.Popen([args.binary],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=r/'v2/.qa',env=os.environ.copy())
selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ);buffer=b''
def send(value):proc.stdin.write((json.dumps(value)+'\n').encode());proc.stdin.flush()
def receive():
 global buffer
 until=time.monotonic()+10
 while b'\n' not in buffer:
  assert selector.select(max(0,until-time.monotonic())),'production process timeout'
  chunk=os.read(proc.stdout.fileno(),65536);assert chunk,'production process EOF: '+proc.stderr.read().decode()[-2000:];buffer+=chunk
 line,buffer=buffer.split(b'\n',1);return json.loads(line)
ids={}
def request(id,method,params):
 ids[id]='h:'+str(uuid.uuid4());send(dict(type='request',id=ids[id],method=method,params=params))
def reply(item,value):send(dict(type='response',id=item['id'],result=value))
report=[]
try:
 hello=receive();assert hello['type']=='hello' and hello['sdkVersion']=='0.1.1'
 request('init','initialize',dict(protocol=1,extensionId=hello['id'],platform='macOS',packageDir=str(r/'v2'),dataDir=str(r/'v2/.qa/data'),tempDir=str(r/'v2/.qa/tmp'),grantedCapabilities=['clipboard.read','clipboard.write','clipboard.pasteText','selection.read'],migrationPaths={}))
 assert receive()['result']['ready'] is True
 for index,(case,oracle) in enumerate(zip(inputs,oracles)):
  command=case['command'];sid='diff-'+str(index);opening='open-'+sid
  request(opening,'session.open',dict(sessionId=sid,commandName=('copy-to-clipboard' if command=='copy' else 'paste-from-clipboard'),preferences={},argumentValues={}))
  read=receive();assert read['method']==('host.selection.read' if command=='copy' else 'host.clipboard.read')
  assert read['params']==({'kind':'text'} if command=='copy' else {'format':'content'})
  reply(read,case['source'] if command=='copy' else {'text':case['source'],'hasFiles':False})
  message=receive();effects=[]
  if message['type']=='request':
   assert message['method']==('host.clipboard.write' if command=='copy' else 'host.clipboard.pasteText')
   assert set(message['params'])=={'text'};effects.append([command,message['params']['text']]);reply(message,{'ok':True});message=receive()
  assert message['type']=='response' and message['id']==ids[opening]
  result=message['result'];assert result['mode']=='no-view'
  expected_effects=[f for f in oracle['flow'] if f[0] in ['copy','paste']]
  hud=[f[1] for f in oracle['flow'] if f[0]=='HUD']
  exact=effects==expected_effects and (not hud or result.get('message')==hud[-1])
  report.append(dict(name=case['name'],command=command,exact=exact,effects=effects,sourceEffects=expected_effects))
  assert exact,(case['name'],command,result,oracle)
  request('dispose-'+sid,'session.dispose',dict(sessionId=sid));assert 'error' not in receive()
 request('shutdown','shutdown',{});assert 'error' not in receive();proc.stdin.close();proc.wait(timeout=5);assert proc.returncode==0
finally:
 if proc.poll() is None:proc.kill();proc.wait()
 selector.close();proc.stdout.close();proc.stderr.close()
(r/'v2/.qa/production-differential.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'sourceCompilerCases':len(cases),'actualSourceCommandComparisons':len(report),'exact':sum(c['exact'] for c in report),'binary':args.binary,'emittedJavaScriptExecuted':False,'OSAccess':False}))
