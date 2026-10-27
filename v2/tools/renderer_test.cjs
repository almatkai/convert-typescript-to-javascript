'use strict';
// Execute the exact pinned renderer in a closed VM with hooks/bridge stubbed
// before render. No DOM, real window, clipboard, timers, or host profile exists.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const ts=require(path.join(root,'.qa/v1/node_modules/typescript'));
const original=fs.readFileSync(path.join(root,'evidence/host/src/renderer/ExtensionRuntimeView.tsx'),'utf8');
const before=`              if (result.mode === 'no-view') {
                setState((prev) => ({ ...prev, message: undefined }))
                return
              }`;
const after=`              if (result.mode === 'no-view') {
                await window.tezbar.extensionDisposeSession({ sessionId: state.sessionId })
                if (currentSession.current === sessionOwner) onBack()
                return
              }`;
assert.equal(original.split(before).length,2);
const patch=fs.readFileSync(path.join(root,'host-prerequisites/0001-dispose-completed-action-no-view.patch'),'utf8');
assert(patch.includes('-                setState((prev) => ({ ...prev, message: undefined }))')&&patch.includes('+                await window.tezbar.extensionDisposeSession({ sessionId: state.sessionId })'));
async function run(source,stale=false){
 const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 const context=vm.createContext(Object.create(null),{codeGeneration:{strings:false,wasm:false}});
 new vm.Script(`
 const events=[];const refs=[];
 const window={tezbar:{extensionInvokeAction:async()=>({ok:true,mode:'no-view',message:'Copied code to clipboard'}),extensionDisposeSession:async p=>{events.push(['dispose',p.sessionId]);${stale?"refs.find(r=>r.current==='owned-session:g').current='another-session';":''}return true;}},setTimeout:()=>1,clearTimeout:()=>{}};
 const console={log:()=>{},error:()=>{}};
 const react={useCallback:f=>f,useEffect:()=>{},useState:i=>[typeof i==='function'?i():i,()=>{}],useRef:i=>{const r={current:i};refs.push(r);return r;}};
 const jsx={jsx:(type,props)=>({type,props}),jsxs:(type,props)=>({type,props})};
 function require(name){if(name==='react')return react;if(name==='react/jsx-runtime')return jsx;if(name==='./extensionSessionRefresh')return {startSessionRefresh:()=>()=>{}};if(name==='./ui/primitives')return {Button:'button',Message:'message'};if(name==='./src/raycast-api')return {ExtensionRuntimeSurface:'surface'};throw Error('Blocked renderer import: '+name);}
 const exports={};
 ${compiled}
 const initial={ok:true,mode:'view',sessionId:'owned-session',generation:'g',extensionId:'test',commandName:'test',title:'test',root:{type:'Detail',props:{markdown:'Frozen bytes'}},actions:[{id:'retry:1',title:'Retry Copy — may duplicate',kind:'action'}]};
 const tree=exports.default({initial,onBack:()=>events.push(['back'])});
 function find(node){if(!node||typeof node!=='object')return null;if(node.type==='surface')return node;for(const child of Object.values(node.props||{})){if(Array.isArray(child)){for(const c of child){const r=find(c);if(r)return r;}}else{const r=find(child);if(r)return r;}}return null;}
 const surface=find(tree);if(!surface)throw Error('Missing actual runtime surface');
 `).runInContext(context);
 await new vm.Script("surface.props.onInvokeAction('retry:1',{})").runInContext(context);
 return JSON.parse(new vm.Script('JSON.stringify(events)').runInContext(context));
}
(async()=>{
 assert.deepEqual(await run(original),[],'Pinned renderer retains a recovery session after action no-view');
 assert.deepEqual(await run(original.replace(before,after)),[['dispose','owned-session'],['back']]);
 assert.deepEqual(await run(original.replace(before,after),true),[['dispose','owned-session']]);
 // Disposal belongs to the old session even if navigation changes while awaited.
 // Parent review must test actual desktop navigation, not infer it from this VM.
 const source=fs.readFileSync(path.join(root,'evidence/host/src-tauri/src/native_core/extensions/native.rs'),'utf8');
 assert(source.includes('if value["mode"] != "view" {\n            self.remove(&id);\n            p.dispose(&id).await;'));
 console.log(JSON.stringify({assertions:7,pinnedOriginal:'reproduced missing recovery action disposal',patched:'disposes and returns onBack',hostWrites:false,desktopQA:'not-run'}));
})().catch(error=>{console.error(error);process.exitCode=1;});
