// Trusted original modules only. Submitted TypeScript remains a primitive string
// passed to transformAsync; it is never compiled into a VM script or executed.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const readline = require('node:readline');
const base = path.resolve(__dirname, '../.qa/v1');
const babel = require(path.join(base, 'node_modules/@babel/core'));
const preset = require(path.join(base, 'node_modules/@babel/preset-typescript'));
const ts = require(path.join(base, 'node_modules/typescript'));
const context = vm.createContext(Object.create(null), {codeGeneration:{strings:false,wasm:false}});
let flow = [], text = '', file = false, failRead = false, failEffect = false;
function closed(fn) { Object.setPrototypeOf(fn,null); return Object.freeze(fn); }
const bridge = Object.create(null);
bridge.transform=closed((source, config, complete)=>{
 const options=JSON.parse(config);
 if(typeof source!=='string'||options.filename!=='clipboard.ts'||options.presetCount!==1) {complete(JSON.stringify({error:'oracle config changed'}));return;}
 babel.transformAsync(source,{filename:options.filename,presets:[preset]}).then(
   result=>complete(JSON.stringify({result:result ? {code:result.code} : null})),
   ()=>complete(JSON.stringify({error:'Babel transformation failed'})));
});
bridge.read=closed(()=>{flow.push(['read']);return JSON.stringify(failRead?{error:'read failed'}:{result:{text,file}});});
bridge.selected=closed(()=>{flow.push(['selected']);return JSON.stringify(failRead?{error:'selection failed'}:{result:text});});
bridge.effect=closed((kind,source)=>{flow.push([kind,source]);return JSON.stringify(failEffect?{error:'effect failed'}:{result:null});});
bridge.hud=closed(message=>{flow.push(['HUD',message]);});
Object.freeze(bridge);
context.bridge = bridge;
new vm.Script(`'use strict';
const modules = Object.create(null);
function result(data){const value=JSON.parse(data);if(value.error)throw new Error(value.error);return value.result;}
const api = Object.freeze({Clipboard:Object.freeze({read:async()=>result(bridge.read()),copy:async s=>result(bridge.effect('copy',s)),paste:async s=>result(bridge.effect('paste',s))}),getSelectedText:async()=>result(bridge.selected()),showHUD:async s=>{bridge.hud(s);}});
const babel = Object.freeze({transformAsync:(source,options)=>new Promise((resolve,reject)=>{bridge.transform(source,JSON.stringify({filename:options.filename,presetCount:options.presets.length}),data=>{try{resolve(result(data));}catch(error){reject(error);}});})});
const preset = Object.freeze({});
function require(name){if(name==='@babel/core')return babel;if(name==='@babel/preset-typescript')return preset;if(name==='@raycast/api')return api;if(name==='./internal/typescript-to-javascript')return modules.transform;throw Error('Blocked require: '+name);}
`).runInContext(context);
// Guard checks precede every actual source-module callback.
new vm.Script(`
if(typeof process!=='undefined'||Object.getPrototypeOf(bridge)!==null||Object.getPrototypeOf(bridge.transform)!==null)throw Error('Open oracle environment');
let blocked=false;try{(()=>{}).constructor('return process')();}catch(error){blocked=true;}if(!blocked)throw Error('String evaluation available');
blocked=false;try{require('node:child_process');}catch(error){blocked=true;}if(!blocked)throw Error('Process escape available');
`).runInContext(context);
for (const [key, filePath] of [['transform','src/internal/typescript-to-javascript.ts'],['copy','src/copy-to-clipboard.ts'],['paste','src/paste-from-clipboard.ts']]) {
 const src = fs.readFileSync(path.join(base,filePath),'utf8');
 const compiled = ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
 new vm.Script(`{const exports={};${compiled}\nmodules[${JSON.stringify(key)}]=exports;}`).runInContext(context);
}
(async()=>{
 for await (const line of readline.createInterface({input:process.stdin,crlfDelay:Infinity})) {
  const item=JSON.parse(line);text=item.source;file=item.file||false;failRead=item.failRead||false;failEffect=item.failEffect||false;flow=[];
  try {
   if(item.command){await new vm.Script(`modules[${JSON.stringify(item.command)}].default()`).runInContext(context);console.log(JSON.stringify({flow}));}
   else{context.input=text;console.log(JSON.stringify({code:await new vm.Script('modules.transform.covertTypeScriptToJavaScript(input)').runInContext(context)}));}
  } catch(e){console.log(JSON.stringify({error:e.message,flow}));}
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
