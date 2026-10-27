# Round 2 review status

**Required local gates are green. Exact locked-Babel parity: 343/343.** All prior
264 sources/expected results remain byte-for-byte prefixes of the expanded
fixtures; [ROUND2_BASELINE.json](evidence/ROUND2_BASELINE.json) records the original
serialized hashes. The original ten failure packets and their exact repaired
outputs remain in [REVIEW_BLOCKERS.json](REVIEW_BLOCKERS.json). No generated user
JavaScript was executed. This finite result is not universal compiler equivalence.

## Compiler repairs

Stable enum bindings now resolve through semantic symbol/reference IDs, including
forward declarations, recursive arithmetic/aliases, unary expressions, shadowing,
mutation rejection and cycles. Evaluation has a work counter and active-binding
bound. Nonfinite classification respects binding identity and evaluator visitation
order; dynamic bound NaN/Infinity retain their meaning and Babel purity.

The pinned Rust transformer fork uses symbol IDs for enum declaration/value tables,
preventing nested same-name enums from merging or shadowed member reads from
folding. It evaluates cooked template quasis and reference interpolations, preserves
dynamic templates and Babel reverse-map behavior, classifies dynamic effects, and
rejects implicit members after computed strings. The codegen fork fixes private
field comment attachment, declarator continuations outside loop initializers,
synthesized decimal/negative-zero spelling and escaped tabs.

The 79 added actual locked-Babel cases cover these classes, nested scopes, forward
and circular aliases, reassignment, grouping/precedence, f64/nonfinite/coercion,
static/dynamic templates, string increment, comments and multivar contexts. No
prior fixture was normalized, weakened, excluded or replaced with native output.

## Host prerequisites and desktop acceptance

Three generic patches remain **unapplied**:

- `0001-dispose-completed-action-no-view.patch`: exact renderer callback tests.
- `0002-verified-version-icons-and-installed-aliases.patch`: extracted registry helpers.
- `0003-coherent-clipboard-content.patch`: exact native macOS/Windows snapshot
  producers, wire producer and original/patched routes tested with owned stubs.

The new adapter requests `{format:"content"}` and accepts only closed
`{text:string|null,hasFiles:boolean}`. Files, even with text, suppress delivery.
Malformed metadata/results, legacy STRING, absent/empty text and read failures
produce the source's no-text outcome without delivery. The pinned host lacks this
mode and cannot successfully paste until patch 0003 is reviewed and integrated.
Default/text reads for other extensions remain STRING. The SDK is unchanged.

macOS uses metadata/text reads bracketed by the same board's change count and
rejects change/ambiguity. Windows owns the clipboard lock across metadata and text.
Neither producer reads file URIs or paths. Platform stubs cover text/file/both,
empty/missing text, malformed metadata/text, read failures, macOS race rejection,
and Windows writer exclusion; source callbacks verify the corresponding file guard.
These tests do not replace a full host build or actual desktop verification.

Both macOS and Windows GUI selection, clipboard, focus/paste, recovery disposal,
installed alias/icon routing and launcher acceptance remain **not-run**. The
manifest keeps `artifacts:{}`. Source feature publication is not installation
acceptance. GNU check/Clippy pass; GNU linking lacks dlltool and MSVC is absent.
No installation, publication or deletion was performed.

## Licensing evidence

`r-efi` 6.0.0's exact published AUTHORS contains an MIT grant and copyright notices;
it is retained verbatim. The prior missing-text assertion for that crate was wrong
and is corrected. `assert-unchecked` 0.1.2's exact crate and immutable upstream tree
were inspected, including README and source: Cargo.toml declares MIT but those
trees contain no grant text. Authentic declaration/source/tree evidence remains.
This is a specific evidence limitation, not invented legal approval or a fabricated
mandatory local gate. All 146 dependency licensing records are retained.
