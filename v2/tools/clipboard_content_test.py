#!/usr/bin/env python3
"""Exercise actual patched native clipboard functions with owned OS stubs only.
No clipboard, desktop, file selection, user path or host checkout is accessed.
"""
import difflib,json,os,pathlib,re,subprocess
r=pathlib.Path(__file__).resolve().parents[2];v=r/'v2';q=v/'.qa/clipboard-content';q.mkdir(parents=True,exist_ok=True)
# Apply each hunk with exact context against immutable host evidence.
patch=(v/'host-prerequisites/0003-coherent-clipboard-content.patch').read_text()
files={};current=None;lines=patch.splitlines(True);i=0
while i<len(lines):
 line=lines[i]
 if line.startswith('--- a/'):
  current=line[6:].strip();files[current]=(v/'evidence/host'/current).read_text().splitlines(True);delta=0;i+=2;continue
 if line.startswith('@@'):
  start=int(re.match(r'@@ -(\d+)',line).group(1))-1+delta;i+=1;old=[];new=[]
  while i<len(lines) and not lines[i].startswith(('@@','--- ')):
   line=lines[i]
   if line.startswith((' ','-')):old.append(line[1:])
   if line.startswith((' ','+')):new.append(line[1:])
   i+=1
  assert files[current][start:start+len(old)]==old,'Patch context drift'
  files[current][start:start+len(old)]=new;delta+=len(new)-len(old);continue
 i+=1
files={k:''.join(s) for k,s in files.items()}
native=files['src-tauri/src/native_core/launcher/clipboard_native.rs']
def content(platform):
 start=native.index('    pub fn content()',native.index('#[cfg(target_os = "'+platform+'"'));end=native.index('\n    pub fn files()',start);return native[start:end]
# Source extraction includes actual format routing and JSON producer, not a replica.
host=files['src-tauri/src/native_core/extensions/process_host.rs']
route=host[host.index('"host.clipboard.read"=>'):host.index('\n',host.index('"host.clipboard.read"=>'))].split('=>',1)[1].rstrip(',')
start=host.index('async fn read_clipboard_content()');producer=host[start:host.index('\n}',start)+2]
assert 'pub(crate) mod clipboard_native;' in files['src-tauri/src/native_core/launcher/mod.rs']
code=r'''
#![allow(non_snake_case,dead_code)]
use serde_json::{json,Value};
mod mac {
use std::ffi::{c_char,c_void,CStr,CString};use std::sync::Mutex;
type Id=*mut c_void;
struct State{types:Vec<CString>,text:Option<Vec<u8>>,sequence:usize,race:bool,bad_metadata:bool,bad_type:bool,reads:usize}
static STATE:Mutex<Option<State>>=Mutex::new(None);
struct Pool;impl Pool{unsafe fn new()->Self{Self}}
unsafe fn board()->Id{1usize as Id}unsafe fn class(_: &str)->Id{7usize as Id}
unsafe fn cast<T>(n:usize)->T{assert_eq!(std::mem::size_of::<T>(),std::mem::size_of::<usize>());std::mem::transmute_copy(&n)}
unsafe fn s0<T>(o:Id,n:&str)->T{
 let mut guard=STATE.lock().unwrap();let s=guard.as_mut().unwrap();
 let value=match n {
 "changeCount"=>{s.reads+=1;s.sequence+usize::from(s.race&&s.reads>1)},
 "types"=>if s.bad_metadata{0}else{2},"count"=>s.types.len(),
 "UTF8String"=>if o as usize==4{s.text.as_ref().map_or(0,|s|s.as_ptr() as usize)}else if s.bad_type{0}else{s.types[o as usize-100].as_ptr() as usize},
 _=>panic!("Unexpected platform call {n}")};cast(value)
}
unsafe fn s1<A,T>(_:Id,n:&str,a:A)->T{
 let value=match n{"objectAtIndex:"=>{let index:usize=std::mem::transmute_copy(&a);100+index},"stringWithUTF8String:"=>3,"lengthOfBytesUsingEncoding:"=>STATE.lock().unwrap().as_ref().unwrap().text.as_ref().unwrap().len(),"stringForType:"=>if STATE.lock().unwrap().as_ref().unwrap().text.is_some(){4}else{0},_=>panic!("Unexpected platform call {n}")};cast(value)
}
'''+content('macos')+r'''
#[test]fn actual_macos_producer(){
 for (types,text,expected) in [
 (vec!["public.utf8-plain-text"],Some("const n=1"),Some((Some("const n=1"),false))),
 (vec!["public.file-url"],None,Some((None,true))),
 (vec!["public.file-url","public.utf8-plain-text"],Some("code"),Some((Some("code"),true))),
 (vec![],None,Some((None,false))),
 (vec!["public.utf8-plain-text"],Some(""),Some((Some(""),false))),
 (vec!["public.utf8-plain-text"],Some("x\0y"),Some((Some("x\0y"),false))),
 (vec!["NSFilenamesPboardType"],None,Some((None,true))),
 (vec!["NSFilesPromisePboardType"],None,Some((None,true))),
 (vec!["public.utf8-plain-text"],None,None),
 ] {
  *STATE.lock().unwrap()=Some(State{types:types.iter().map(|s|CString::new(*s).unwrap()).collect(),text:text.map(|s|s.as_bytes().to_vec()),sequence:10,race:false,bad_metadata:false,bad_type:false,reads:0});
  assert_eq!(content().ok(),expected.map(|(s,f)|(s.map(str::to_owned),f)));
 }
 {let mut s=STATE.lock().unwrap();let s=s.as_mut().unwrap();s.bad_metadata=true;}assert!(content().is_err());
 {let mut s=STATE.lock().unwrap();let s=s.as_mut().unwrap();s.bad_metadata=false;s.bad_type=true;}assert!(content().is_err());
 {let mut s=STATE.lock().unwrap();let s=s.as_mut().unwrap();s.bad_type=false;s.text=Some(b"changed".to_vec());s.race=true;s.reads=0;}assert_eq!(content().unwrap_err(),"Clipboard changed during read");
}
}
mod windows {
use std::ffi::c_void;use std::sync::Mutex;type Handle=*mut c_void;
struct State{has_files:bool,has_text:bool,data:Vec<u16>,busy:bool,locked:bool,fail_read:bool,fail_lock:bool,bad_size:bool,closes:usize,unlocks:usize}
static STATE:Mutex<Option<State>>=Mutex::new(None);
unsafe fn OpenClipboard(_:Handle)->i32{let mut g=STATE.lock().unwrap();let s=g.as_mut().unwrap();if s.busy||s.locked{0}else{s.locked=true;1}}
unsafe fn CloseClipboard()->i32{let mut g=STATE.lock().unwrap();let s=g.as_mut().unwrap();assert!(s.locked);s.locked=false;s.closes+=1;1}
unsafe fn IsClipboardFormatAvailable(f:u32)->i32{let g=STATE.lock().unwrap();let s=g.as_ref().unwrap();assert!(s.locked);i32::from(if f==15{s.has_files}else{assert_eq!(f,13);s.has_text})}
unsafe fn GetClipboardData(f:u32)->Handle{assert_eq!(f,13);let g=STATE.lock().unwrap();let s=g.as_ref().unwrap();assert!(s.locked);if s.fail_read{std::ptr::null_mut()}else{1usize as Handle}}
unsafe fn GlobalSize(_:Handle)->usize{let g=STATE.lock().unwrap();let s=g.as_ref().unwrap();if s.bad_size{3}else{s.data.len()*2}}
unsafe fn GlobalLock(_:Handle)->Handle{let g=STATE.lock().unwrap();let s=g.as_ref().unwrap();assert!(s.locked);if s.fail_lock{std::ptr::null_mut()}else{s.data.as_ptr() as Handle}}
unsafe fn GlobalUnlock(_:Handle)->i32{let mut g=STATE.lock().unwrap();let s=g.as_mut().unwrap();assert!(s.locked);s.unlocks+=1;1}
struct Board;impl Drop for Board{fn drop(&mut self){unsafe{CloseClipboard();}}}
'''+content('windows')+r'''
#[test]fn actual_windows_producer(){
 for (has_files,text) in [(false,Some("code 😀")),(true,None),(true,Some("code")),(false,None),(false,Some(""))] {
  *STATE.lock().unwrap()=Some(State{has_files,has_text:text.is_some(),data:text.unwrap_or("").encode_utf16().chain(Some(0)).collect(),busy:false,locked:false,fail_read:false,fail_lock:false,bad_size:false,closes:0,unlocks:0});
  assert_eq!(content().unwrap(),(text.map(str::to_owned),has_files));
  let g=STATE.lock().unwrap();let s=g.as_ref().unwrap();assert!(!s.locked);assert_eq!(s.closes,1);
 }
 {let mut g=STATE.lock().unwrap();g.as_mut().unwrap().busy=true;}assert!(content().is_err());
 {let mut g=STATE.lock().unwrap();let s=g.as_mut().unwrap();s.busy=false;s.fail_read=true;}assert!(content().is_err());
 {let mut g=STATE.lock().unwrap();let s=g.as_mut().unwrap();s.fail_read=false;s.bad_size=true;}assert!(content().is_err());
 {let mut g=STATE.lock().unwrap();let s=g.as_mut().unwrap();s.bad_size=false;s.fail_lock=true;}assert!(content().is_err());
 {let mut g=STATE.lock().unwrap();let s=g.as_mut().unwrap();s.fail_lock=false;s.data=vec![65];}assert!(content().is_err());
 {let mut g=STATE.lock().unwrap();let s=g.as_mut().unwrap();s.data=vec![0xd800,0];}assert!(content().is_err());
 // Another writer cannot open while the snapshot owns the clipboard.
 unsafe{assert_eq!(OpenClipboard(std::ptr::null_mut()),1);assert_eq!(OpenClipboard(std::ptr::null_mut()),0);CloseClipboard();}
 let g=STATE.lock().unwrap();let s=g.as_ref().unwrap();assert!(!s.locked);assert!(s.unlocks>=3);
}
}
// The extracted async wire producer uses the same tuple-to-closed-JSON mapping.
type CoreResult=Result<Value,String>;
mod native_core{pub mod launcher{pub mod clipboard_native{pub fn content()->Result<(Option<String>,bool),String>{Ok((Some("owned".into()),false))}}}}
async fn read_clipboard_image()->CoreResult{Ok(json!("image"))}
struct Ctx;impl Ctx{async fn request(&self,channel:&str,_:Vec<Value>)->CoreResult{assert_eq!(channel,"clipboard:read");Ok(json!("legacy"))}}
struct Host{ctx:Ctx}impl Host{async fn route(&self,params:Value)->CoreResult{
'''+route+r'''
}}
'''+producer+r'''
#[tokio::test]async fn actual_wire_producer_and_route(){
 let host=Host{ctx:Ctx};assert_eq!(host.route(json!({"format":"content"})).await.unwrap(),json!({"text":"owned","hasFiles":false}));
 assert_eq!(host.route(json!({"format":"text"})).await.unwrap(),"legacy");assert_eq!(host.route(json!({})).await.unwrap(),"legacy");
 assert!(host.route(json!({"format":"unknown"})).await.is_err());
}
'''
# Execute the exact pinned text-only producer with owned arboard results.
original=(v/'evidence/host/src-tauri/src/native_core/launcher/clipboard.rs').read_text()
a=original.index('                return match self.native()?.get_text()');b=original.index('\n            }',a)
arm=original[a:b]
original_host=(v/'evidence/host/src-tauri/src/native_core/extensions/process_host.rs').read_text()
a=original_host.index('"host.clipboard.read"=>');old_route=original_host[a:original_host.index('\n',a)].split('=>',1)[1].rstrip(',')
code+='\nmod pinned_text {\nuse super::*;\n'+r'''
mod arboard{#[derive(Clone)]pub enum Error{ContentNotAvailable,ReadFailed}impl std::fmt::Display for Error{fn fmt(&self,f:&mut std::fmt::Formatter<'_>)->std::fmt::Result{write!(f,"owned read error")}}}
struct Clipboard{result:Result<String,arboard::Error>}impl Clipboard{fn get_text(&self)->Result<String,arboard::Error>{self.result.clone()}}
struct Worker{clipboard:Clipboard}impl Worker{fn native(&self)->Result<&Clipboard,String>{Ok(&self.clipboard)}fn read(&self)->CoreResult{
'''+arm+r'''
}}
#[test]fn actual_pinned_string_producer(){
 let worker=Worker{clipboard:Clipboard{result:Ok("owned file-plus-text".into())}};assert_eq!(worker.read().unwrap(),"owned file-plus-text");
 let worker=Worker{clipboard:Clipboard{result:Err(arboard::Error::ContentNotAvailable)}};assert_eq!(worker.read().unwrap(),"");
 let worker=Worker{clipboard:Clipboard{result:Err(arboard::Error::ReadFailed)}};assert!(worker.read().is_err());
}
impl Host{async fn pinned_route(&self,params:Value)->CoreResult{
'''+old_route+r'''
}}
#[tokio::test]async fn actual_pinned_route_lacks_content_mode(){
 let host=Host{ctx:Ctx};assert!(host.pinned_route(json!({"format":"content"})).await.is_err());assert_eq!(host.pinned_route(json!({"format":"text"})).await.unwrap(),"legacy");
}
}
'''
# Production Win32 ABI imports remain present in the real patch.
assert 'fn IsClipboardFormatAvailable(format: u32) -> i32;' in native and 'fn GlobalSize(h: Handle) -> usize;' in native
(q/'src').mkdir(exist_ok=True);(q/'src/lib.rs').write_text(code)
(q/'Cargo.toml').write_text('[package]\nname="actual-clipboard-content-producers"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\nserde_json="=1.0.140"\ntokio={version="=1.44.2",features=["rt-multi-thread","macros"]}\n')
env=os.environ.copy();env['CARGO_TARGET_DIR']=str(q/'target')
subprocess.run(['cargo','+1.85.0','test','--offline','--manifest-path',str(q/'Cargo.toml')],env=env,check=True)
print(json.dumps({'actualPatchedProducers':['macOS','Windows','wire JSON','format route'],'platformAccess':'owned stubs only','hostPatch':'unapplied','GUI':'not-run'}))
