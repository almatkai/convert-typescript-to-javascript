# Native Rust v2 — review candidate

**Round 2 source review candidate.** Exact locked-Babel parity is **343/343**;
all original 264 cases and their expected bytes are retained, with 79 fresh actual
oracle cases. Required local gates pass on Rust 1.85.0 and stable. Finite coverage
does not establish universal Babel parity. Host prerequisites remain unapplied and
both desktop acceptance states remain `not-run`; this is not an installed or
accepted release. See [VALIDATION.md](VALIDATION.md) and
[REVIEW_BLOCKERS.md](REVIEW_BLOCKERS.md).

This is a schema-3 standalone Rust executable using protocol 1 and the production
SDK 0.1.1 over immutable HTTPS revision
`e955911f0bf5b558f9d3eb5183df0adc95c22af2`. There is no Tauri adapter registration,
local SDK path dependency, JavaScript engine, submitted-code execution, subprocess
compiler, server transpilation, or runtime Node/Bun requirement.

## Command behavior

- `paste-from-clipboard`: request a coherent clipboard content snapshot, reject files,
  transform its nonempty text once, automatically call
  `host.clipboard.pasteText` once. That host operation owns clipboard/focus/hide/paste.
- `copy-to-clipboard`: read text selection, transform once, automatically call
  `host.clipboard.write` once. A fresh normal command can deliberately copy again.

Successful effects require the closed response `{ok:true,message?:string}`.
Null, booleans, unknown fields, contradictory/error fields, and invalid messages
are unconfirmed. A positive ACK returns SDK no-view success. Acquisition failure
and absent/empty text preserve the V1 message `No text found in clipboard`.
Parser/transform failures preserve V1's generic transformation error. V1's helper
also rejects an empty generated program, which remains an error here.

An unconfirmed effect opens a deliberate recovery view holding the exact frozen
JavaScript bytes. The retry action warns that the effect may already have happened
and retry may duplicate it. It never reads input, transforms, or clocks again.
Tokens are consumed before awaiting, outside SDK staged state; stale/repeated
queued actions are inert. Cancellation before acquisition commits prevents delivery;
after dispatch, completion may be unknown. There is no exactly-once or crash/restart
durability claim. Closing/disposal frees in-memory recovery bytes.

Selection acquisition retains the pinned STRING contract. Clipboard acquisition
explicitly requests `{format:"content"}` and accepts only the closed response
`{text:string|null,hasFiles:boolean}`. Files always suppress delivery, including
file-plus-text. Missing/empty text, malformed/extra fields, legacy STRING, unknown
shapes and read errors fail closed without transformation or delivery.

The pinned host has no content mode: its typed route rejects that format and its
legacy clipboard producer returns only STRING. Therefore successful paste requires
the separately reviewed [unapplied generic content patch](host-prerequisites/0003-coherent-clipboard-content.patch).
There is no fallback to a text-only read. The existing SDK transports opaque JSON;
no SDK change is needed. On macOS the patch reads advertised file flavors and text
between change-count fences; a change or ambiguous metadata returns an error.
On Windows it holds `OpenClipboard` while reading CF_HDROP availability and
CF_UNICODETEXT. It never reads file paths/URLs. Default/text mode remains STRING.

## Native compiler and source contract

The original transform is `babel.transformAsync(input, {filename:'clipboard.ts',
presets:[presetTypescript]})`, from locked core/preset 7.22.5; locked parser and
generator are 7.28.5. No preset-react, preset-env, tsc options, execution, or REPL
feature is inferred. TSX and decorators rejected by that configuration remain
errors. Ambient external Babel configuration is not consulted by native code;
the oracle uses an isolated copy of this actual package, which has no such config.

OXC parser/semantic/transformer 0.58.0 supplies the Rust AST. `compat.rs` implements
Babel-specific AST adjustments. The private genuine Rust `vendor/oxc_codegen` fork
implements output and comment seams. `vendor/oxc_transformer` fixes enum tables to
use semantic SymbolId, nonfinite resolution, cooked template interpolation,
dynamic purity, exact string reverse-map classification, and string auto-increment
errors. Upstream pins, hashes, and authentic licenses are retained for both forks.
All formerly failing cases remain mandatory exact tests;
there is no fixture lookup, output normalization, excluded failure, success override,
or added syntax denylist. Stable binding folds use semantic references, a cycle
set, at most 128 active bindings, and an 8192-step work budget per evaluation.
They implement a finite static expression subset, never execute expressions.
Beyond these folding budgets/subset, dynamic output may differ from Babel; the
343-case result is the measured claim.

## Bounds and ownership

Input is at most 64 KiB UTF-8. A conservative raw delimiter counter rejects depth
above 128; a raw segment between `; { } [ ] ,` is at most 4096 Unicode scalars.
These guards include strings/comments and can reject otherwise valid large text.
Generated output is checked after codegen and is at most 512 KiB UTF-8. There is no
truncation. These limits bound accepted source/output, not peak allocator usage
or a hard synchronous compiler CPU deadline. Compiler invariant panics become a
bounded generic error; stack-overflow/allocator failure is not claimed recoverable.

There are at most 128 adapter entries (about 64 MiB of frozen output at their
individual limits, excluding JSON, AST/transient allocations and runtime stacks).
Session IDs are at most 256 bytes. Each reverse RPC has a 10-second deadline;
manifest command timeout is 30 seconds. Host error contents are never echoed into
recovery. Recovery output remains below the SDK/host 16 MiB frame ceiling, including
JSON escaping. The runtime owns two worker threads with 64 MiB stacks; the pinned
SDK owns its bounded stdio pump. No detached helpers, polling threads, background
leases, or periodic timers are introduced.

An open-drop guard handles SDK cancellation without adapter disposal. Owner-context
pruning on the next open also handles cancellation between adapter return and SDK
state commit. Recovery state and token consumption never depend on staged `Value`.

## Reproduce inside this clone

Existing Rust stable/1.85.0, Node/npm and Python 3.9+ are used; scripts install no
toolchain or global tool. Source `tools/env.sh` from the selected clone root before
any dependency materialization. All mutable state, Cargo/npm homes, temp/cache,
source copies, archives and extraction stay under `v2/.qa`, `v2/target`, `v2/dist`.
`RUSTUP_HOME` only selects the already-installed toolchains; auto-install is disabled.

```sh
. v2/tools/env.sh
python3 v2/tools/prepare_qa.py
python3 v2/tools/verify.py
```

`verify.py` exits nonzero while any mandatory gate fails. It continues independent
checks and saves their logs and exit codes in `v2/.qa`; the Round 2 run has 20
passing required gates.
`prepare_qa.py` materializes only the exact original npm lock with scripts disabled.
Oracle VM scripts compile the trusted original extension modules; submitted
TypeScript is only a parser/transform input string and generated output is never run.
Host APIs, timers, React hooks and producer effects are stubbed before callbacks.

The source and pinned host/SDK bytes are hashable under `evidence/`. `audit.py`
checks the V1-byte boundary, pins, icon, dependency license evidence and empty Git
index. To rehash the complete candidate before parent review:

```sh
python3 v2/tools/finalize.py --write
python3 v2/tools/finalize.py
```

Parent must independently rehash the eventual staged blobs before committing.
No commit, push, PR, release, installation, deletion, host/SDK/profile change, or
root workflow activation is performed by these scripts.

## Development archive and host prerequisite

```sh
cargo +1.85.0 build --locked --release --manifest-path v2/Cargo.toml
python3 v2/tools/package_dev.py
python3 v2/tools/process_test.py --binary "$PWD/v2/dist/extracted/bin/tezbar-convert-typescript-to-javascript"
python3 v2/tools/production_differential.py --binary "$PWD/v2/dist/extracted/bin/tezbar-convert-typescript-to-javascript"
```

The ignored ARM64 development ZIP uses fixed timestamps/modes and a closed complete
SHA256 file inventory. Its source/packaged manifests have `artifacts:{}` and invent
no release/catalog/acquisition URLs. Archive determinism means identical package
inputs yield identical ZIP bytes; cross-machine compiler reproducibility is not
claimed. This review archive must not be published as an accepted implementation.

The pinned host already disposes initial no-view sessions. Its renderer retains a
session after a recovery action returns no-view. The exact pinned renderer is
executed in an isolated hook/bridge VM to reproduce that behavior and verify the
minimal [unapplied generic disposal patch](host-prerequisites/0001-dispose-completed-action-no-view.patch).
The second [unapplied patch](host-prerequisites/0002-verified-version-icons-and-installed-aliases.patch)
resolves embedded icons from the verified active version and declared aliases from
verified installed packages, independent of the built-in catalog. Exact original
and patched registry helpers are compiled in an isolated owned Rust harness; the
whole host is not built or mutated. Preference/data roots are retained.
Applying and desktop-testing all three patches belongs to parent host integration.
Source feature publication would not establish installation acceptance.
The new clipboard test executes exact original/patched producers and routing with
owned platform stubs: text-only, file-only, file-plus-text, absent/empty text,
malformed metadata, read failures, macOS races and Windows lock exclusion.
The real SDK process tests reject legacy STRING and malformed content shapes.

macOS and Windows desktop acceptance are both `not-run` in the manifest. Windows
GNU check/Clippy pass; native GNU linking is blocked by missing `dlltool`, and the
MSVC target is absent. These facts do not imply Windows GUI verification.
See [VALIDATION.md](VALIDATION.md) for this candidate's observed results.
