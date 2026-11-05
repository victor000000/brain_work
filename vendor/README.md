# Vendored sources

Third-party source copied into this repository rather than installed as
opaque binaries. Both are MIT licensed; their `LICENSE` files are kept beside
the code.

## fastplus

**What:** `py-fastplus` — a Rust/PyO3 parser for the WorldQuant Fast Expression
language. Parses an alpha expression into an AST and, *for operators it knows*,
checks argument count, argument type and operator-specific rules.

**Version:** 0.3.5 · **Licence:** MIT (© 2026 AshSwing) · **Upstream:** PyPI
`py-fastplus` (no project URL published)

**Vendored from:** the PyPI sdist, so this is the complete buildable source —
Rust crate, PEG grammar, Python shim.

**Why vendored:** the grammar file `src/fastplus.pest` is the authoritative
statement of what a Fast Expression is. It answers questions the behaviour
alone does not:

```pest
operation   = { VARIABLE ~ "(" ~ args ~ ")" }    // any identifier, no whitelist
PLACEHOLDER = @{ "<" ~ VARIABLE ~ "/>" }         // template syntax is first-class
primary     = { operation | PLACEHOLDER | VARIABLE | CONSTANT | "(" ~ expression ~ ")" }
```

That is why `totally_made_up_operator(close)` and `vector_neut(x,<name/>)`
both parse. It also documents the contract precisely: checks apply **when
parsing known operators** (`在解析已知操作符时`), so unknown names pass by
design, not by defect.

**Known gap:** the error enum declares `UnknownOperator`, `UnknownVariable`
and `UnresolvedPlaceholder`, and **nothing in the crate constructs any of
them** — `parser.rs:386` returns `Ok(())` when `get_operator` misses. So
operator-name validation was intended and never wired. `generator/validate.py`
compensates with an allowlist read from the `operators` table.

### Decision: not patching it

Wiring that check is a two-line change — `return Ok(())` becomes
`return Err(...)`, and the caller at `parser.rs:266` already turns the message
into a spanned `PestError`. We are deliberately not doing it.

The reason is that the package **documents** the current behaviour
(`在解析已知操作符时` — checks apply when parsing *known* operators), so patching
it makes our fork contradict its own README. A future version bump would
silently revert the patch, and the failure mode would be invisible: invented
operators would start passing again, and nothing would say so.

The Python allowlist is the better home for this check because it is visible in
our test suite, works without the Rust build in environments that only install
the wheel, and is independent of a toolchain we cannot guarantee everywhere.
`validate.py` documents it as the layer fastplus intentionally does not
provide.

**Building:** requires a Rust toolchain and maturin.

```bash
make fastplus        # maturin build from vendor/fastplus
```

## cnhkmcp

**What:** a Model Context Protocol server for WorldQuant BRAIN. The wheel is
71 MB, but most of it is a Flask web app and an 11 MB Windows installer; only
the knowledge and template material is vendored here.

**Version:** 4.3.8 · **Licence:** MIT (© 2024 CNHK) · **Upstream:** PyPI
`cnhkmcp`

| Path | Contents |
|---|---|
| `knowledge/` | 74 BRAIN documentation pages as JSON — **stale**, see below |
| `skills/` | 23 skill definitions (markdown + data) |
| `templates/templates.json` | 5 templates in `<placeholder/>` + `templateConfigurations` form |
| `template_summary.txt` | 3,182 lines — the curated forum template collection |

**Staleness:** the bundled `knowledge/` copy stops around **2025-03**. The live
pages were last modified between **2026-08-25 and 2026-09-24**. Current copies
were harvested to `docs/learn/` via `tools/harvest_learn_docs.py`; this
vendored copy is kept for provenance and for the skills, which have no
upstream API.

**The most valuable artefact** is `template_summary.txt` — a human-curated
collection with hypothesis, settings and logic-chain analysis per template,
parsed by `tools/parse_cnhkmcp_templates.py`. It is what the mined-forum
corpus (10,045 skeletons, unfiltered user text) is measured against.
