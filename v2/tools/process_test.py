#!/usr/bin/env python3
"""Production JSONL process tests with owned fake pipes; never OS effects."""
import argparse,json,os,pathlib,selectors,subprocess,time,uuid
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=argparse.ArgumentParser();P.add_argument('--binary',default=str(ROOT/'v2/target/debug/tezbar-convert-typescript-to-javascript'));args=P.parse_args()
COUNT=0

def check(ok,message='assertion failed'):
 global COUNT
 assert ok,message
 COUNT+=1

class Host:
 def __init__(self):
  self.p=subprocess.Popen([args.binary],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT/'v2/.qa',env=os.environ.copy())
  self.selector=selectors.DefaultSelector();self.selector.register(self.p.stdout,selectors.EVENT_READ);self.buffer=b'';self.saved=[];self.calls=[]
  hello=self.next();check(hello['type']=='hello' and hello['id']=='com.tezbar.native.convert-typescript-to-javascript' and hello['sdkVersion']=='0.1.1')
  request=self.request('initialize',dict(protocol=1,extensionId=hello['id'],platform='macOS',packageDir=str(ROOT/'v2'),dataDir=str(ROOT/'v2/.qa/data'),tempDir=str(ROOT/'v2/.qa/tmp'),grantedCapabilities=['clipboard.read','clipboard.write','clipboard.pasteText','selection.read'],migrationPaths={}))
  check(self.response(request)['result']['ready'] is True)
 def send(self,v):
  self.p.stdin.write((json.dumps(v,ensure_ascii=True)+'\n').encode());self.p.stdin.flush()
 def request(self,method,params):
  id='h:'+str(uuid.uuid4());self.send(dict(type='request',id=id,method=method,params=params));return id
 def next(self,timeout=5):
  end=time.monotonic()+timeout
  while b'\n' not in self.buffer:
   ready=self.selector.select(max(0,end-time.monotonic()))
   if not ready:raise AssertionError('process timeout')
   chunk=os.read(self.p.stdout.fileno(),65536)
   if not chunk:raise AssertionError('process exited: '+self.p.stderr.read().decode()[-2000:])
   self.buffer+=chunk
  line,self.buffer=self.buffer.split(b'\n',1);return json.loads(line)
 def reply(self,request,value=None,error=None):
  data=dict(type='response',id=request['id'])
  if error is None:data['result']=value
  else:data['error']={'code':'test','message':error}
  self.send(data)
 def response(self,id,handler=None,timeout=5):
  deadline=time.monotonic()+timeout
  while True:
   for index,item in enumerate(self.saved):
    if item.get('type')=='response' and item.get('id')==id:return self.saved.pop(index)
   item=self.next(max(.1,deadline-time.monotonic()))
   if item.get('type')=='response' and item.get('id')==id:return item
   if item.get('type')=='request':
    self.calls.append(item)
    if handler:handler(item)
    else:raise AssertionError('Unexpected reverse RPC: '+str(item))
   elif item.get('type')!='cancel':self.saved.append(item)
 def open(self,sid,command='copy-to-clipboard'):
  return self.request('session.open',dict(sessionId=sid,commandName=command,preferences={},argumentValues={}))
 def call(self,sid,operation,payload=None):return self.request('session.call',dict(sessionId=sid,operation=operation,payload=payload or {}))
 def dispose(self,sid):
  result=self.response(self.request('session.dispose',dict(sessionId=sid)));check('error' not in result)
 def close(self):
  try:
   self.response(self.request('shutdown',{}));self.p.stdin.close();self.p.wait(timeout=5);check(self.p.returncode==0)
  finally:
   if self.p.poll() is None:self.p.kill();self.p.wait()
   self.selector.close();self.p.stdout.close();self.p.stderr.close()

def automatic(host,command,source,ack={'ok':True},read_error=None,effect_error=None,sid=None):
 sid=sid or str(uuid.uuid4());methods=[]
 def handler(req):
  methods.append(req['method'])
  if len(methods)==1:
   check(req['params']==({'format':'content'} if command=='paste-from-clipboard' else {'kind':'text'}))
   host.reply(req,({'text':source,'hasFiles':False} if command=='paste-from-clipboard' and isinstance(source,str) else source),error=read_error)
  else:
   check(req['params']=={'text':'const value = 1;'},'Unexpected transformed delivery')
   host.reply(req,ack,error=effect_error)
 result=host.response(host.open(sid,command),handler)['result'];return sid,result,methods

h=Host()
try:
 for command,read,effect in [('copy-to-clipboard','host.selection.read','host.clipboard.write'),('paste-from-clipboard','host.clipboard.read','host.clipboard.pasteText')]:
  sid,result,methods=automatic(h,command,'const value: number = 1;')
  check(result['mode']=='no-view');check(methods==[read,effect]);h.dispose(sid)
  # A fresh normal command can deliberately copy/paste again.
  sid,result,methods=automatic(h,command,'const value: number = 1;');check(len(methods)==2);h.dispose(sid)
 # Closed rich content contract: all malformed/ambiguous/file-bearing inputs
 # must finish without a transform/effect. A pinned legacy STRING fails closed.
 for content in ['const value:number=1;', None, True, {}, {'text':'const value:number=1;'},
  {'text':'const value:number=1;','hasFiles':True}, {'text':None,'hasFiles':True},
  {'text':None,'hasFiles':False}, {'text':'','hasFiles':False},
  {'text':'const value:number=1;','hasFiles':0}, {'text':'const value:number=1;','hasFiles':None},
  {'text':'const value:number=1;','hasFiles':False,'unknown':True}, {'text':True,'hasFiles':False}]:
  sid=str(uuid.uuid4());seen=[]
  def content_reply(req):
   seen.append(req['method']);check(req['method']=='host.clipboard.read');check(req['params']=={'format':'content'});h.reply(req,content)
  result=h.response(h.open(sid,'paste-from-clipboard'),content_reply)['result']
  check(result['mode']=='no-view' and result['message']=='No text found in clipboard' and seen==['host.clipboard.read']);h.dispose(sid)
 sid,result,methods=automatic(h,'paste-from-clipboard',None,read_error='owned snapshot changed')
 check(result['message']=='No text found in clipboard' and len(methods)==1);h.dispose(sid)
 for source in ['',None,True,{}, {'text':'const value:number=1;'},'type T = number;','const value: = 1;','x'*(65536+1),'('*129+'1'+')'*129]:
  sid,result,methods=automatic(h,'copy-to-clipboard',source)
  check(result['mode']=='no-view' and len(methods)==1);h.dispose(sid)
 sid,result,methods=automatic(h,'copy-to-clipboard',None,read_error='sensitive host text'*1000)
 check(result['message']=='No text found in clipboard');h.dispose(sid)
 for ack in [None,True,False,{}, {'ok':False}, {'ok':True,'error':'contradiction'}, {'ok':True,'extra':1}, {'ok':True,'message':None}]:
  sid,result,methods=automatic(h,'copy-to-clipboard','const value:number=1;',ack=ack)
  check(result['mode']=='view' and 'may already have happened' in result['root']['props']['markdown'])
  check(result['actions'][0]['kind']=='action');old=result['actions'][0]['id'];check(old=='retry:1')
  # Stale, guessed, and unrelated operations never reread or redeliver.
  for action in ['retry:0','unknown',{},'retry:9999999999999999999999999999999999']:
   check(h.response(h.call(sid,'extension:invoke-action',{'actionId':action}))['result']['mode']=='unchanged')
  refreshed=h.response(h.call(sid,'extension:refresh-session'))['result'];check(refreshed['root']==result['root'])
  retry=h.call(sid,'extension:invoke-action',{'actionId':old});request=h.next();check(request['method']=='host.clipboard.write' and request['params']=={'text':'const value = 1;'})
  h.reply(request,{'ok':True,'message':'confirmed'});check(h.response(retry)['result']['mode']=='no-view')
  check(h.response(h.call(sid,'extension:invoke-action',{'actionId':old}))['result']['mode']=='unchanged');h.dispose(sid)
 # Host error after dispatch is also unknown, without leaking arbitrary host text.
 sid,result,_=automatic(h,'paste-from-clipboard','const value:number=1;',effect_error='private\n'*1000)
 check(result['mode']=='view' and 'private' not in str(result));h.dispose(sid)
 # Cancellation during retry: outside-state token remains consumed and exact bytes remain.
 sid,result,_=automatic(h,'copy-to-clipboard','const value:number=1;',ack=None)
 token=result['actions'][0]['id'];call=h.call(sid,'extension:invoke-action',{'actionId':token});req=h.next();check(req['method']=='host.clipboard.write')
 h.send(dict(type='cancel',requestId=call,reason='owned test cancellation'))
 check('error' in h.response(call))
 h.reply(req,{'ok':True}) # A late reply never changes ownership or causes a replay.
 check(h.response(h.call(sid,'extension:invoke-action',{'actionId':token}))['result']['mode']=='unchanged')
 recovered=h.response(h.call(sid,'extension:refresh-session'))['result'];check(recovered['actions'][0]['id']=='retry:2');check(recovered['root']==result['root']);h.dispose(sid)
 # Dispose while effect pending: no additional requests, late ACK ignored.
 sid='dispose-pending';opening=h.open(sid);read=h.next();h.reply(read,'const value:number=1;');effect=h.next();dispose=h.request('session.dispose',{'sessionId':sid})
 check('error' in h.response(opening));check('error' not in h.response(dispose));h.reply(effect,{'ok':True})
 # More than SDK capacity of cancelled opens without adapter dispose callbacks.
 for index in range(140):
  sid='cancel-'+str(index);opening=h.open(sid);read=h.next();check(read['method']=='host.selection.read');h.send(dict(type='cancel',requestId=opening,reason='cancel before acquisition commit'))
  check('error' in h.response(opening));h.reply(read,'const neverDelivered:number=1;')
 sid,result,_=automatic(h,'copy-to-clipboard','const value:number=1;');check(result['mode']=='no-view');h.dispose(sid)
 # Cancel after the effect reply can race adapter-return/SDK commit. Either
 # terminal wire outcome is legitimate; orphaned adapter owners must be pruned.
 for index in range(140):
  sid='cancel-commit-'+str(index);opening=h.open(sid);read=h.next();h.reply(read,'const value:number=1;');effect=h.next();h.reply(effect,None)
  h.send(dict(type='cancel',requestId=opening,reason='cancel at open commit boundary'))
  response=h.response(opening)
  if 'result' in response:h.dispose(sid)
 # UTF-8 / recovery JSON keeps exact frozen bytes through unknown responses.
 sid='unicode';opening=h.open(sid);read=h.next();h.reply(read,'const café: string = "你好😀";');effect=h.next();expected='const café = "你好😀";';check(effect['params']['text']==expected);h.reply(effect,None)
 view=h.response(opening)['result'];frozen=json.loads(view['root']['props']['markdown'].split('```json\n')[1].split('\n```')[0]);check(frozen.encode()==expected.encode())
 action=h.call(sid,'extension:invoke-action',{'actionId':view['actions'][0]['id']});effect=h.next();check(effect['params']['text'].encode()==expected.encode());h.reply(effect,{'ok':True});check(h.response(action)['result']['mode']=='no-view');h.dispose(sid)
 # Retry overlap uses SDK reject-while-busy; queued/stale tokens cannot dispatch twice.
 sid,result,_=automatic(h,'copy-to-clipboard','const value:number=1;',ack=None);token=result['actions'][0]['id']
 a=h.call(sid,'extension:invoke-action',{'actionId':token});effect=h.next();b=h.call(sid,'extension:invoke-action',{'actionId':token});check('error' in h.response(b));h.reply(effect,{'ok':True});check(h.response(a)['result']['mode']=='no-view');h.dispose(sid)
 # Capacity returns an honest error, disposal restores it.
 for index in range(128):
  sid='capacity-'+str(index);_,result,_=automatic(h,'copy-to-clipboard','const value:number=1;',ack=None,sid=sid);check(result['mode']=='view')
 check('error' in h.response(h.open('capacity-overflow')))
 for index in range(128):h.dispose('capacity-'+str(index))
 sid,result,_=automatic(h,'copy-to-clipboard','const value:number=1;');check(result['mode']=='no-view');h.dispose(sid)
 # Per-effect timeout (10 s) yields recovery, preserving exact bytes and no retry.
 sid='timeout';opening=h.open(sid);read=h.next();h.reply(read,'const value:number=1;');effect=h.next()
 timed=h.response(opening,timeout=13)['result'];check(timed['mode']=='view');check('const value = 1;' in timed['root']['props']['markdown']);h.reply(effect,{'ok':True});h.dispose(sid)
finally:h.close()
# EOF with an unresolved reverse call exits; no OS service or child user code exists.
h=Host();opening=h.open('eof');request=h.next();h.p.stdin.close();h.p.wait(timeout=5);check(h.p.returncode==0);h.selector.close();h.p.stdout.close();h.p.stderr.close()
for option in ['--protocol-info','--self-test']:
 result=subprocess.run([args.binary,option],cwd=ROOT/'v2/.qa',env=os.environ.copy(),capture_output=True,text=True,check=True)
 check(bool(result.stdout.strip()))
h=Host()
try:
 try:h.p.stdin.write(b'{'+b' '*(16*1024*1024)+b'}\n');h.p.stdin.flush()
 except BrokenPipeError:pass
 try:h.p.stdin.close()
 except BrokenPipeError:pass
 h.p.wait(timeout=5);check(h.p.returncode!=0)
finally:
 if h.p.poll() is None:h.p.kill();h.p.wait()
 h.selector.close();h.p.stdout.close();h.p.stderr.close()
print(json.dumps({'assertions':COUNT,'cancelledOpens':140,'cancelAtCommitRaces':140,'capacity':128,'binary':args.binary,'OSIntegration':'not-run'}))
