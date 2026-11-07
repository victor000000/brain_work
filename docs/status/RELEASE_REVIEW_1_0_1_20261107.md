# Release review: 1.0.0 → 1.0.1 — November 7, 2026

## Scope and design review

Project metadata declared 1.0.0. No separate next-release version was found;
preserve that sequence with a focused 1.0.1 patch. Existing Expert design,
semantic guard, quota and reconciliation changes are ongoing work, not replaced.
The working tree contains substantial earlier edits/deletions/untracked work;
none were reset or staged. No release was published or activated; subsequent local commit details appear below.

Reproduced defect: `classify_leaf('pv87_eps_forward')`,
`pv87_ebit_normalized_scale`, `pv87_ebt_actual_scale` and
`pv87_total_assets_scale` returned `pv`. Python regex word boundaries treat
underscores as word characters. This defeats meaning-before-prefix filtering.

Design: recognize EPS/EBIT/EBT/assets tokens using alphanumeric boundaries,
including underscore-delimited tokens. Preserve classification precedence,
resolver interfaces, operator handling and existing submission ownership.
Reject these tokens under option prefixes too. Do not broaden the patch into
an unreviewed parser replacement or metadata acquisition pipeline.

Critical self-review: substring matching must not turn `steps`, `ebitwise`,
`epslike` or `assetsproxy` into these exact semantic tokens. Tests pin that
boundary. Name classification remains a heuristic, not proof of field meaning;
the metadata inventory in the Expert design is still necessary. This patch
does not implement atom-count enforcement or claim all dispatch paths are safe.

## Implementation and final review

- `pyproject.toml`: version 1.0.1.
- `core/scope.py`: correct semantic token boundaries; move regex import to
  normal import section and format the touched module. Preserve the readable
  operator vocabulary with an explained SIM905 exemption.
- `tests/test_scope_meaning.py`: add 12 prefix/token cases, four longer-word
  controls and two in-memory submission-path regressions. The latter verify
  no description PATCH/submission POST/request intent occurs for the violation.
- Final test review corrected an assumption: the request table is created
  lazily, so verify its absence rather than query a nonexistent table.

## Validation evidence

- Guarded whole Python suite: **1638 passed, 16 skipped**, 155.19 seconds.
  Command: `PYTHONPATH=. .venv/bin/python brain_logs/run_quarter_goal_tests_20261021.py`.
  The reviewed harness blocks both raw DuckDB and compatibility opens of the
  production database before opening it; isolates log/budget/ledger paths.
  Log: `/tmp/brain-work-1.0.1-tests.log`.
- Focused scope/category/submission-ownership tests: **61 passed**.
- Touched source/tests: Ruff lint and format pass; module mypy and Bandit pass.
- Broader mypy: **270 source files, no issues**.
- Vulture: no findings at confidence 80.
- Whole-tree Ruff: **168 findings**; format check: **43 files** need formatting.
  These include existing research files and unrelated earlier work; no global
  formatting or automatic fixes were applied. Logs under
  `/tmp/brain-work-1.0.1-{lint,format,types,deadcode}.log`.
- Source-directory Bandit reports **two low-severity B110 findings** in
  `core/quota.py:91` and `core/reconciliation.py:58` (silent persistence errors).
  This patch does not fix them; they remain release-wide review blockers.
  Log: `/tmp/brain-work-1.0.1-security-source.log`.
- The initial repository-recursive Bandit command also entered `.venv`; it was
  stopped and replaced with explicit first-party source directories. No result
  from that interrupted scan is used as a passing gate.
- Rust/parser code unchanged; Rust tests were not rerun for this Python regex
  patch. No live auth, API simulations, submissions, DB inspection or service
  lifecycle operation was used for validation.

## Related repository classification and bounded local patches

The portfolio coordinator verified fork parents; local READMEs establish role.
Fork identity alone does not prove lack of maintenance, but no independent
runtime deliverable requiring a release was identified in these three scopes:

| Repository | Classification and action |
|---|---|
| WorldQuant_alpha101_code | Historical formula examples; fork of yli188/WorldQuant_alpha101_code. Existing five-test offline CI from the earlier review; excluded from mandatory new release, no formula/performance claim. |
| WQ-Brain | Fork of RussellDash332/WQ-Brain; separate upstream/reference integration, not a brain_work dependency. Excluded from mandatory release; no auth/run performed. |
| worldquant-miner | Fork of zhutoutoutousan/worldquant-miner; upstream/reference strategy collection with separate service requirements. Excluded; no model services or automatic miners launched. |
| Alphas02 | Owned educational notebook deliverable, not trading infrastructure. No previous declared version; establish **0.0.3** locally. Reject duplicate code-cell metadata ids so one exercise exemption cannot be reused. Synthetic regression plus existing video tests: **3 passed**; checker validates **3 notebooks/82 cells/8 exercises/2 YAML configs**. |
| alphas3 | Owned research-script deliverable, not the active brain_work writer. No previous declared version; establish **0.0.3** locally. Hunyuan previously reported a randomly selected model but always requested t1; request the chosen model. Mock-SDK test forces turbos and verifies returned content and request identity. **5 tests passed**, tracked-source checker parsed **13 Python files**. |

Related changes are in `/home/vic/github-cleanup-20261105/work-Alphas02` and
`/home/vic/github-cleanup-20261105/work/alphas3-clean`, with local VERSION and
RELEASE_REVIEW.md files. Both checkouts were clean before this work. No other
worktrees, upstream fork code or remote branches were changed. Checks exercised
synthetic notebooks/mock provider objects only; no real SDK/auth/training or
profitability claim. Their release notes document assumptions and limitations.

Local related-project commits (both on `main`, no push):
Alphas02 `317e0368b0cade40cf2a270f089fbee0df161ff2`;
alphas3 `45164c4e78e8d3728b1faf4eefba0128436661bc`.
Both working trees were clean after committing.

## Remaining conditions

1. Repository-wide quality gates are not all green. Do not describe 1.0.1 as a
   fully approved or deployed release on the strength of the focused patch.
2. Existing semantic scope collection can abstain on malformed/missing native
   expression payloads; a future fail-closed change needs lifecycle/ownership
   tests, especially for already-owned requests. Not fixed here.
3. Atom-only policy still needs structural field/dependency validation and
   reviewed partition handling across dispatch routes. No regex-only guarantee.
4. Whole-portfolio scope/atom compliance and Expert promotion remain unverified.
   No running interpreter was restarted to load the patch.

## Publication checkout and commit scope

The original research tree has mixed earlier changes, so coherent release source
is committed in `/home/vic/.local/share/project-publications/brain_work-20261105`,
the established sanitized owning-repository checkout. Prerequisite commit
`706ae9c` preserves the semantic helper and its submission caller/tests on top of
the previously tested credential/ownership baseline. The following 1.0.1 commit
contains the boundary correction, new regression cases, version and design.
Original research-tree edits remain in place for the active Expert owner.

The existing CI already installs hash-pinned dependencies in a clean venv and
runs full offline unit tests plus static/native-parser checks. This release
adds JUnit output to that hosted unit run; it does not replace the full suite
with focused tests. Local publication `make ci` results are recorded separately
from the original working-tree results above.

The Expert design references retained local evidence reports. These private
research snapshots are intentionally not copied into the public source tree.

## Final publication validation and remote status

`CARGO_BUILD_JOBS=2 make ci` exited **0** in the sanitized publication checkout:
**1624 Python tests passed, 16 corpus tests skipped; 22 Rust tests passed**.
Whole-tree format, Ruff, mypy (267 source files), Bandit and Vulture all passed.
Log: `/tmp/brain-work-publication-1.0.1-ci.log`. Dependency metadata checked with
`uv pip check --python .venv/bin/python`: 43 packages compatible. This local
uv-provisioned venv has no pip module; the existing hosted workflow creates a
normal Python venv and explicitly installs hash-pinned requirements with pip.
No fresh hosted environment or run is claimed. A focused JUnit invocation
passed all 24 semantic-meaning cases and produced 24 XML testcase records.

The research tree's 1638-test result and broader static findings above apply to
that separate mixed tree. The smaller sanitized release suite does not include
unrelated unfinished quota/reconciliation research changes. Do not confuse the
two trees or attribute all research-tree changes to this patch.

The GitHub connector mutation test returned **403 Resource not accessible by
integration**. Central coordination also verified no credentials from the
noninteractive Git helper and rejected existing SSH keys; no new keys or UI
permission changes were made. Therefore **push and new exact-SHA hosted CI are
blocked**, despite passing local CI. No prior successful run proves these new
commits passed on GitHub.

Read-only branch checks still show these remote main heads:
- brain_work: `7bd22977aa6249fe557a02863abb7e5b9d700824`
- Alphas02: `7f0fd1ad2a9969e2fdf5165e3e9c2a9bee4e1aa4`
- alphas3: `5f0213b5f2d83b17282d0cbeedf3ec652b36cc0c`

All three reviewed release changes have local commits; no force push, amend,
live research or service change was performed. Original research-tree copies
remain uncommitted alongside earlier work; the isolated publication checkout
is the coherent committed brain_work release source.
