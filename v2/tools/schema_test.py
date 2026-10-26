#!/usr/bin/env python3
"""Offline validator for all assertion keywords used by the pinned host schema.
This deliberately does not claim to implement arbitrary JSON Schema vocabularies.
"""
import argparse,copy,json,pathlib,re,urllib.parse
ROOT=pathlib.Path(__file__).resolve().parents[2]
SCHEMA=json.loads((ROOT/'v2/evidence/host/schemas/extension-v3.schema.json').read_text())
def validate(value,schema):
 if '$ref' in schema:
  node=SCHEMA
  for part in schema['$ref'].split('/')[1:]:node=node[part]
  validate(value,node)
 for part in schema.get('allOf',[]):validate(value,part)
 if 'const' in schema:assert value==schema['const'] and type(value)==type(schema['const'])
 if 'enum' in schema:assert value in schema['enum']
 typ=schema.get('type');kinds=typ if isinstance(typ,list) else [typ] if typ else []
 if kinds:
  checks={'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),'integer':type(value)==int,'number':type(value) in [float,int],'boolean':type(value)==bool,'null':value is None}
  assert any(checks[k] for k in kinds)
 if isinstance(value,dict):
  assert all(k in value for k in schema.get('required',[]))
  assert len(value)<=schema.get('maxProperties',float('inf'))
  for k,v in value.items():
   if 'propertyNames' in schema:validate(k,schema['propertyNames'])
   if k in schema.get('properties',{}):validate(v,schema['properties'][k])
   elif schema.get('additionalProperties') is False:raise AssertionError('additional property '+k)
   elif isinstance(schema.get('additionalProperties'),dict):validate(v,schema['additionalProperties'])
 if isinstance(value,list):
  assert len(value)>=schema.get('minItems',0) and len(value)<=schema.get('maxItems',float('inf'))
  if schema.get('uniqueItems'):assert len(set(map(lambda x:json.dumps(x,sort_keys=True),value)))==len(value)
  for item in value:
   if 'items' in schema:validate(item,schema['items'])
 if isinstance(value,str):
  assert len(value)>=schema.get('minLength',0) and len(value)<=schema.get('maxLength',float('inf'))
  if 'pattern' in schema:assert re.search(schema['pattern'],value)
  if schema.get('format')=='uri':assert urllib.parse.urlsplit(value).scheme
 if type(value) in [float,int]:assert value>=schema.get('minimum',-float('inf')) and value<=schema.get('maximum',float('inf'))
def check_manifest(manifest):
 validate(manifest,SCHEMA)
 assert manifest['artifacts']=={},'Review candidate must not invent acquisition artifacts'
 assert manifest['capabilities']==['clipboard.read','selection.read','clipboard.write','clipboard.pasteText']
 assert {c['name'] for c in manifest['commands']}=={'paste-from-clipboard','copy-to-clipboard'}
 assert manifest['replaces']==['com.tezbar.convert-typescript-to-javascript','raycast.convert-typescript-to-javascript']
 assert all(v['state']=='not-run' for v in manifest['verification'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,default=ROOT/'v2/extension.json');args=p.parse_args()
 m=json.loads(args.manifest.read_text());check_manifest(m);negatives=[]
 for key,value in [('schemaVersion',2),('runtime','javascript'),('execution','embedded'),('protocolVersion',2),('id','raycast.bad'),('capabilities',['host.eval']),('replaces',[]),('commands',[]),('files',{'../escape':'0'*64}),('artifacts',{'wrong':{}})]:
  n=copy.deepcopy(m);n[key]=value;negatives.append(n)
 for key,value in [('runtime','native'),('platforms',[]),('timeoutMs',300001),('refreshMs',100),('concurrency','parallel')]:
  n=copy.deepcopy(m);n['commands'][0][key]=value;negatives.append(n)
 for n in negatives:
  try:validate(n,SCHEMA)
  except AssertionError:pass
  else:raise AssertionError('Schema accepted negative '+repr(n))
 print(json.dumps({'valid':1,'schemaNegatives':len(negatives),'schemaPin':'ea100cee3f69711de12485ba061950c5fc65258f','validator':'offline pinned-keyword interpreter'}))
