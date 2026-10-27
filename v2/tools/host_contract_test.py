#!/usr/bin/env python3
"""Compile actual pinned/patched registry helpers against owned fixture stubs.
This is not a host build, install, desktop test, or OS clipboard operation.
"""
import os,pathlib,subprocess,json,re
r=pathlib.Path(__file__).resolve().parents[2];v=r/'v2';q=v/'.qa/host-contract';q.mkdir(parents=True,exist_ok=True)
# Apply the exact unapplied patch to owned copies, checking every hunk context.
patch=(v/'host-prerequisites/0002-verified-version-icons-and-installed-aliases.patch').read_text()
files={}
for f in ['src-tauri/src/native_core/extensions/registry.rs','src-tauri/src/native_core/extensions/native.rs']:
 text=(v/'evidence/host'/f).read_text();lines=patch.splitlines(True);active=False;i=0;delta=0
 while i<len(lines):
  line=lines[i]
  if line.startswith('--- '):active=line.strip()=='--- a/'+f;i+=1;continue
  if active and line.startswith('@@'):
   start=int(re.match(r'@@ -(\d+)',line).group(1))-1+delta
   i+=1;old=[];new=[]
   while i<len(lines) and not lines[i].startswith(('@@','--- ')):
    line=lines[i]
    if line.startswith((' ','-')):old.append(line[1:])
    if line.startswith((' ','+')):new.append(line[1:])
    i+=1
   source=text.splitlines(True);assert source[start:start+len(old)]==old,'Patch context drift';source[start:start+len(old)]=new;delta+=len(new)-len(old);text=''.join(source);continue
  i+=1
 files[f]=text
reg=files['src-tauri/src/native_core/extensions/registry.rs']
def function(name,text=None):
 reg=text if text is not None else files['src-tauri/src/native_core/extensions/registry.rs']
 start=reg.index('fn '+name+'(');start=reg.rfind('\n',0,start)+1;end=reg.index('\n}',start)+2;return reg[start:end]
code='''use serde_json::{json,Value};
use std::{collections::HashSet,path::{Path,PathBuf,Component}};
#[derive(Clone)]struct Installed{id:String,slug:String,path:PathBuf,package_dir:Option<PathBuf>,manifest:Value}
struct CoreContext{entries:Vec<Installed>}
fn collect(ctx:&CoreContext)->Vec<Installed>{ctx.entries.clone()}
fn fallback<'a>(v:&'a Value,key:&str,default:&'a str)->&'a str{v[key].as_str().unwrap_or(default)}
'''
# pub(super) is valid inside this module, as in the original host hierarchy.
code='mod extracted {\n'+code+'\n'+function('icon_path')+'\n'+function('command_icon_path')+'\n'+function('replacement_id')+'\n'
fixture=q/'fixture/extensions/packages/com.tezbar.native.fixture/versions/active';fixture.mkdir(parents=True,exist_ok=True);(fixture/'resources').mkdir(exist_ok=True);(fixture/'resources/icon.png').write_bytes((v/'resources/icon.png').read_bytes())
# Use a Rust raw string literal for the owned path; no shell interpolation.
code+='''
#[test]fn actual_helpers_resolve_only_verified_version_files_and_declared_aliases(){
 let root=PathBuf::from(r#"'''+str(fixture)+'''"#);
 let mut entry=Installed{id:"com.tezbar.native.fixture".into(),slug:"fixture".into(),path:root.parent().unwrap().parent().unwrap().to_path_buf(),package_dir:Some(root.clone()),manifest:json!({"icon":"resources/icon.png","files":{"resources/icon.png":"hash-verified-by-stubbed-resolve"},"replaces":["raycast.fixture","com.tezbar.fixture"]})};
 assert_eq!(icon_path(&entry),Some(root.join("resources/icon.png").to_string_lossy().into_owned()));
 assert_eq!(command_icon_path(&entry,&json!({"icon":"resources/icon.png"})),icon_path(&entry));
 assert_eq!(command_icon_path(&entry,&json!({"icon":"../escape"})),None);
 assert_eq!(command_icon_path(&entry,&json!({"icon":"resources/not-in-inventory.png"})),None);
 let ctx=CoreContext{entries:vec![entry.clone()]};
 assert_eq!(replacement_id(&ctx,"raycast.fixture").unwrap(),Some(entry.id.clone()));
 assert_eq!(replacement_id(&ctx,"com.tezbar.fixture").unwrap(),Some(entry.id.clone()));
 assert_eq!(replacement_id(&ctx,"fixture").unwrap(),None);
 assert_eq!(replacement_id(&ctx,"raycast.other").unwrap(),None);
 entry.package_dir=None;assert_eq!(icon_path(&entry),None);
 entry.manifest["healthError"]=json!("tampered");assert_eq!(replacement_id(&CoreContext{entries:vec![entry.clone()]},"raycast.fixture").unwrap(),None);
 entry.manifest["healthError"]=Value::Null;entry.id="com.tezbar.native.other".into();
 assert!(replacement_id(&CoreContext{entries:vec![ctx.entries[0].clone(),entry]},"raycast.fixture").is_err());
}
}
'''
original=(v/'evidence/host/src-tauri/src/native_core/extensions/registry.rs').read_text()
base=code[code.index('use serde_json'):code.index('fn icon_path')]
code+='\nmod original {\n'+base+function('icon_path',original)+'\n'+function('command_icon_path',original)+'''
#[test]fn pinned_original_cannot_find_active_version_icon(){
 let root=PathBuf::from(r#"'''+str(fixture)+'''"#);
 let entry=Installed{id:"com.tezbar.native.fixture".into(),slug:"fixture".into(),path:root.parent().unwrap().parent().unwrap().to_path_buf(),package_dir:Some(root),manifest:json!({"icon":"resources/icon.png"})};
 assert_eq!(icon_path(&entry),None);
 assert_eq!(command_icon_path(&entry,&json!({"icon":"resources/icon.png"})),None);
}
}
'''
(q/'src').mkdir(exist_ok=True);(q/'src/lib.rs').write_text(code)
(q/'Cargo.toml').write_text('[package]\nname="pinned-host-contract-fixture"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\nserde_json="=1.0.140"\n')
env=os.environ.copy();env['CARGO_TARGET_DIR']=str(q/'target')
subprocess.run(['cargo','+1.85.0','test','--offline','--manifest-path',str(q/'Cargo.toml')],env=env,check=True)
# Check routing additions in the exact patched native source without executing it.
native=files['src-tauri/src/native_core/extensions/native.rs'];assert 'registry::replacement_id(ctx, requested)?' in native
assert 'requested.starts_with("com.tezbar.") || requested.starts_with("raycast.")' in native
print(json.dumps({'registryHelperAssertions':13,'nativeRoutingSourceAssertions':2,'hostBuild':False,'hostWrites':False,'desktopQA':'not-run'}))
