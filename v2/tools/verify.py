#!/usr/bin/env python3
"""Required gates. A failed exact-parity gate always produces nonzero exit."""
import json,os,pathlib,subprocess,sys,time
r=pathlib.Path(__file__).resolve().parents[2];assert pathlib.Path.cwd().resolve()==r
for name in ['HOME','TMPDIR','CARGO_HOME','npm_config_cache','XDG_CACHE_HOME','CARGO_TARGET_DIR']:
 assert pathlib.Path(os.environ[name]).is_relative_to(r/'v2'),'Source tools/env.sh before verification'
checks=[
 ('audit',['python3','v2/tools/audit.py']),
 ('v1-test',['npm','--prefix','v2/.qa/v1','test']),
 ('v1-typecheck',['npm','--prefix','v2/.qa/v1','run','typecheck']),
]
for toolchain in ['1.85.0','stable']:
 checks.extend([(f'fmt-{toolchain}',['cargo','+'+toolchain,'fmt','--manifest-path','v2/Cargo.toml','--all','--','--check']),
 (f'clippy-{toolchain}',['cargo','+'+toolchain,'clippy','--locked','--manifest-path','v2/Cargo.toml','--all-targets','--','-D','warnings']),
 (f'test-{toolchain}',['cargo','+'+toolchain,'test','--locked','--manifest-path','v2/Cargo.toml','--all-targets'])])
checks.extend([
 ('production-build',['cargo','+1.85.0','build','--locked','--manifest-path','v2/Cargo.toml','--all-targets']),
 ('babel-parity',['python3','v2/tools/differential.py']),
 ('source-flow',['python3','v2/tools/source_flow.py']),
 ('renderer',['node','v2/tools/renderer_test.cjs']),
 ('schema',['python3','v2/tools/schema_test.py']),
 ('host-contract',['python3','v2/tools/host_contract_test.py']),
 ('clipboard-content',['python3','v2/tools/clipboard_content_test.py']),
 ('process',['python3','v2/tools/process_test.py']),
 ('production-differential',['python3','v2/tools/production_differential.py','--binary',str(r/'v2/target/debug/tezbar-convert-typescript-to-javascript')]),
 ('windows-gnu-check',['cargo','+stable','check','--locked','--manifest-path','v2/Cargo.toml','--target','x86_64-pc-windows-gnu']),
 ('windows-gnu-clippy',['cargo','+stable','clippy','--locked','--manifest-path','v2/Cargo.toml','--all-targets','--target','x86_64-pc-windows-gnu','--','-D','warnings'])])
results=[]
for name,command in checks:
 log=r/'v2/.qa'/('gate-'+name+'.log')
 with log.open('wb') as stream:result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
 results.append({'gate':name,'exitCode':result.returncode,'command':command,'log':log.relative_to(r).as_posix()})
 print(name,'PASS' if result.returncode==0 else 'FAIL',flush=True)
(r/'v2/.qa/gates.json').write_text(json.dumps(results,indent=2)+'\n')
sys.exit(any(r['exitCode'] for r in results))
