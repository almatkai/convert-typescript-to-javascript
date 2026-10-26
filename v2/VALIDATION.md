# Observed Round 2 validation — 2026-10-26

**All 20 required local gates pass. Exact locked-Babel parity: 343/343.** The
original 264 sources/expected objects are unchanged serialized prefixes, with 79
fresh actual oracle cases. Both production commands also pass **686/686** actual
source-callback comparisons through the real SDK process, including the extracted
ARM64 executable. No submitted/transformed JavaScript was executed.

## Required gates

- audit: **PASS**, exit 0. `v2/.qa/gate-audit.log`.
- v1-test: **PASS**, exit 0. `v2/.qa/gate-v1-test.log`.
- v1-typecheck: **PASS**, exit 0. `v2/.qa/gate-v1-typecheck.log`.
- fmt-1.85.0: **PASS**, exit 0. `v2/.qa/gate-fmt-1.85.0.log`.
- clippy-1.85.0: **PASS**, exit 0. `v2/.qa/gate-clippy-1.85.0.log`.
- test-1.85.0: **PASS**, exit 0. `v2/.qa/gate-test-1.85.0.log`.
- fmt-stable: **PASS**, exit 0. `v2/.qa/gate-fmt-stable.log`.
- clippy-stable: **PASS**, exit 0. `v2/.qa/gate-clippy-stable.log`.
- test-stable: **PASS**, exit 0. `v2/.qa/gate-test-stable.log`.
- production-build: **PASS**, exit 0. `v2/.qa/gate-production-build.log`.
- babel-parity: **PASS**, exit 0. `v2/.qa/gate-babel-parity.log`.
- source-flow: **PASS**, exit 0. `v2/.qa/gate-source-flow.log`.
- renderer: **PASS**, exit 0. `v2/.qa/gate-renderer.log`.
- schema: **PASS**, exit 0. `v2/.qa/gate-schema.log`.
- host-contract: **PASS**, exit 0. `v2/.qa/gate-host-contract.log`.
- clipboard-content: **PASS**, exit 0. `v2/.qa/gate-clipboard-content.log`.
- process: **PASS**, exit 0. `v2/.qa/gate-process.log`.
- production-differential: **PASS**, exit 0. `v2/.qa/gate-production-differential.log`.
- windows-gnu-check: **PASS**, exit 0. `v2/.qa/gate-windows-gnu-check.log`.
- windows-gnu-clippy: **PASS**, exit 0. `v2/.qa/gate-windows-gnu-clippy.log`.

Stable is installed Rust 1.98.0; MSRV is installed Rust 1.85.0. Strict root Clippy
uses `--locked --all-targets -- -D warnings` on both. The Rust differential test is
mandatory on both toolchains. `verify.py` returns nonzero for any failed gate.

## Source, process, and host evidence

- The original V1 one-test suite and strict typecheck run in the disposable exact
  source/npm-lock copy. Original V1 tracked bytes remain unchanged except the
  exact short README link; no dependency/script upgrade was made.
- The closed VM loads actual original helper/commands with filename clipboard.ts
  and the locked preset-only configuration. Producer stubs and escape denials are
  installed before callbacks. There are 343 helper fixtures, 16 locked flow
  fixtures and 686 real command/production-process comparisons. Generated user
  JavaScript is never evaluated.
- Original fixture-prefix hashes are preserved in `evidence/ROUND2_BASELINE.json`;
  `audit.py` now checks them. Current fixture hashes/pins are in `PROVENANCE.json`.
- Production pipe assertions: normal gate **1054**, final isolated Cargo Home
  release **1054**, extracted release **1054**. Runs preserve 140
  acquisition-cancelled opens, 140 adapter-return/SDK-commit cancellation races,
  capacity 128, strict/unknown/contradictory ACKs, frozen Unicode retries,
  consumption before await outside SDK staged rollback, late replies, timeout,
  disposal, EOF, CLI probes and the 16 MiB framing boundary. Assertion totals may
  differ slightly with legitimate commit/cancel races. No real OS effect ran.
- Clipboard acquisition requests only `{format:"content"}`. Owned pipe cases
  reject file-plus-text, file-only, legacy STRING, absent/empty text, missing or
  nonboolean metadata, extra/unknown shapes and read failures without delivery.
  Selection stays STRING. Automatic delivery/no-view behavior and recovery remain.
- The exact pinned renderer callbacks retain the prior 7 VM assertions for the
  generic unapplied no-view disposal repair. Exact registry helpers retain 13 Rust
  assertions plus 2 native routing source assertions for the icon/alias patch.
- Clipboard prerequisite testing compiles **5 tests** extracting actual pinned and
  patched native functions, actual wire producer and format routes. Owned AppKit
  and Win32 stubs cover text-only, file-only, both, absent/empty/NUL-containing
  text, malformed metadata/UTF-16/text, read failures, macOS change-count races,
  Windows busy clipboard and writer exclusion. The pinned route rejects content;
  its old producer returns STRING. No file URL/path, real clipboard, or host
  working file is read. Full host compilation and GUI testing were not run.
- All 19 immutable host evidence files were independently compared against exact
  Git objects at ea100cee3f69711de12485ba061950c5fc65258f. SDK remains HTTPS revision
  e955911f0bf5b558f9d3eb5183df0adc95c22af2, version 0.1.1, without path dependency.
- Source and extracted manifests pass the pinned-schema keyword interpreter;
  all 15 negative manifests are rejected. This is validation of the assertion
  vocabulary used by that exact schema, not arbitrary JSON Schema support.
- Windows GNU check and all-target Clippy pass. A separate native binary build
  again fails because x86_64-w64-mingw32-dlltool is absent. MSVC is not installed.
  Nothing was installed; no Windows runtime/GUI result is claimed.

## Fresh source build and closed development archive

A new isolated Cargo Home and target directory under v2/.qa fetched the immutable
SDK from HTTPS and resolved exact locked crate sources with Rust 1.85.0. The final
source was rebuilt in that isolated environment; its helper passes 343/343 and its
real production process passes the assertions above. The release is Mach-O ARM64.
The archive was generated twice from the same final binary/package inputs with
identical bytes, closed inventory, and fixed modes/timestamps; its actual extracted
production process passes 686 source comparisons and the lifecycle suite.
Cross-machine/compiler reproducibility is not claimed.

- Archive: `convert-typescript-to-javascript-2.0.0-aarch64-apple-darwin-development.zip`
- Archive SHA256: `730073df1f4801f96e8b7bdf3de81e9b458d0e0ca1a9d7d7a131e39559328e4b`
- Executable SHA256: `68621ca4937fba0daae8162e2cf0542c3522e80b48a876c36890e34067e36b0e`
- Closed archive members: 276.
- Original icon SHA256: `85b7bf3d3bc91f315896d165b95e6d40ef72ac71a6ef0e861f1e81a4f675d5bd`.

The ignored archive/extraction is a development review artifact. `artifacts:{}`
and both platform `not-run` states remain in source and package manifests. No
release/catalog/acquisition URL, installation or publication is created.

## Limits and remaining acceptance

Input remains 64 KiB; conservative raw depth 128; raw segments 4096 scalars; output
512 KiB after codegen. Stable-binding folding has a cycle guard, at most 128 active
bindings and an 8192-step evaluation budget, with bounded intermediate strings.
The finite static expression subset and budgets can preserve dynamic output where
Babel folds. These are not peak-heap, hard CPU-deadline or universal-parity claims.
SDK frames are 16 MiB and reverse RPC deadlines 10 seconds. There is no exactly-once
or crash-durable delivery claim.

Three generic host patches are **unapplied**. The pinned host cannot successfully
paste with the required rich guard until content mode is integrated. Successful
source feature review/publication would not establish installation acceptance.
Both macOS and Windows real selection, clipboard metadata, focus/paste, recovery
navigation, icons/aliases and launcher GUI acceptance remain **not-run**.

Licensing evidence retains all 146 resolved records. r-efi's authentic published
AUTHORS contains the MIT grant and copyright notices and is now included verbatim;
the prior filename-only gap claim is corrected. assert-unchecked's exact published
and immutable upstream trees contain an MIT declaration but no grant text, including
README/source review; that precise evidence limit is recorded without fabricated
text or a made-up legal approval gate.

No commit, staging, push, PR, release, installation, deletion, subdelegation,
host/SDK/sibling/profile/ledger change or root workflow activation occurred. Only
the selected clone is changed. All mutable QA/cache/source/extraction data remains
within it. Parent must independently inspect/hash eventual staged blobs.

## Search and candidate hashing

The canonical XERJ prefix ax-f112bc0467fa was used. A bounded refresh ended with
exit 3: frozen docs mapping refused 190 files (defs keyword/text mismatch), and
52 detected source files produced no indexed records. The index is incomplete;
no schema mutation, restart, alternate prefix or bypass occurred. Full file reads,
exact rg/Git checks and the candidate inventory are the audit sources. Diagnostic:
`v2/.qa/round2-xerj-final.log`.

`INVENTORY.sha256` covers every Git-visible v2 file plus root README, excluding only
the inventory itself. Ignored .qa, target, dist, archives, node_modules and bytecode
are excluded and audit-checked. Relevant QA log hashes are retained in
`evidence/validation-log-hashes.json`.
