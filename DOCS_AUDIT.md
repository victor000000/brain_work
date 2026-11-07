# Documentation audit — November 7, 2026

## Scope and lineage

Owned public source is based on remote `a4dab71604bf378ef086a533e6e29a57e8927133`, version 1.0.1. Its tree matched the previously reviewed local release. All maintained topic guides, root guides, template/platform reference wrappers, tools guide, dated Expert proposal and prior release report were inventoried below. This audit is separate from immutable release evidence.

## Inventory and disposition

| Document | Disposition |
|---|---|
| `ARCHITECTURE.md` | Reviewed/revised against published implementation and deployment boundary. |
| `BRAIN_CONSTRAINTS.md` | Historical reference retained; scope/date/current-guide qualification added. |
| `BRAIN_FIELD_RULES.md` | Historical reference retained; scope/date/current-guide qualification added. |
| `BRAIN_RULES.md` | Historical reference retained; scope/date/current-guide qualification added. |
| `BRAIN_SUBMIT_RULES.md` | Reviewed/revised against published implementation and deployment boundary. |
| `PUBLICATION.md` | Reviewed/revised against published implementation and deployment boundary. |
| `README.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/CONFIGURATION.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/CREDENTIAL_MIGRATION.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/DATA.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/DEVELOPMENT.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/EMAIL_RESEARCH.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/EXPERT_PV_OPTIONS_DESIGN_20261107.md` | Dated proposal retained; publication note/private-evidence links corrected. |
| `docs/OPERATIONS.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/README.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/RESEARCH.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/SETUP.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/TEMPLATE_CATALOG.md` | Historical reference retained; scope/date/current-guide qualification added. |
| `docs/TROUBLESHOOTING.md` | Reviewed/revised against published implementation and deployment boundary. |
| `docs/cnhkmcp-templates.md` | Historical reference retained; scope/date/current-guide qualification added. |
| `docs/forum-templates.md` | Historical reference retained; scope/date/current-guide qualification added. |
| `docs/status/RELEASE_REVIEW_1_0_1_20261107.md` | Dated release evidence retained unchanged; new audit is separate. |
| `tools/README.md` | Reviewed/revised against published implementation and deployment boundary. |
| `vendor/README.md` | Reviewed provenance wrapper, retained; upstream manuals excluded from owned rewrite. |
| `DOCS_AUDIT.md` | Current audit coverage, checks and limitations. |

The checker covers 25 owned Markdown documents including this audit. Vendored manuals/skills retain their upstream provenance and are not rewritten as project instructions. The vendor wrapper is checked. Fenced examples, external URL availability, reference-style/HTML links and arbitrary inline-code paths are not validated by the Markdown checker.

## Native/private documentation coverage

The native research checkout was inventoried separately (snapshot while the Expert owner remains active), not inferred from public README coverage: 31 root/top-level-doc/tools-guide candidates, 28 dated status Markdown records, 7 historical archive documents, 7 provider handoff documents, 9 research evidence Markdown records, 1 external-archive README, 19 other Markdown documents and 142 third-party Markdown documents (environment/build directories excluded). The 31 candidates include dated Expert/agent/pyramid/redesign records, not 31 evergreen guides.

Common canonical guides were compared with native copies and source. Seventeen native maintained guides were subsequently revised and committed locally in a separate docs-only commit. The public guides describe the exact published release; private code changes, live authorization/owner handoffs, TODO/agent instructions, provider contracts and raw archives remain with their owning native workflow and were not overwritten or exported into this publication. The active Expert chat independently owns changing runtime/research handoffs. Dated private observations remain evidence, not public runtime instructions; the private per-path inventory includes hashes and disposition. No claim is made to have revalidated every underlying private dataset or rewritten third-party/forum content.

## Material corrections and rationale

- Removed public links to absent private handoffs and active/paused/schedule assertions that source cannot certify. Current state belongs to the deployment owner.
- Setup/README now distinguish hashed offline CI bootstrap from uv runtime setup, service installation and external-effect startup. Added the omitted nonsecret service-unit source template required by `make install-service`; only offline rendering and make dry-run were exercised.
- Research/architecture/submission guides distinguish name-based semantic screening from field provenance, structural atom policy and native acceptance. Explicitly document guard abstention and missing structural atom/partition validation.
- Data/operations retain sole-writer, WAL and no-replay contracts; avoid a fixed UTC quota-reset assumption. Migration documents read-only WAL-recovery preconditions, verification scope and rollback limitations.
- Corrected CLI guidance: email uses `--dry-run` (still remote discovery), not nonexistent `--discover-only`; progress CLI treats its argument as a date, not argparse help. Reconciliation is GET plus local state updates, not a submission CLI.
- Preserved dated platform/template counts and historical studies with current-guide qualification instead of falsifying old results. Historical strategy explanations remain claims requiring evidence.
- Clarified project boundaries: providers own acquisition, screeners own risk/execution UI, and BRAIN acceptance is independent of both.

## Doc-check implementation and verification

`scripts/check_docs.py` is standard-library-only. It checks inline relative links and Markdown heading fragments (including duplicate/Unicode headings), refuses repository escapes, excludes fenced examples, vendor internals, venvs and caches, and never opens DB/network. Five synthetic unit cases cover its relevant behavior. `make docs-check` is included in `make ci` and hosted workflow; no new third-party action is needed.

Safe checks: canonical local links/anchors; source/config defaults and version metadata inspection; migration/export/email argparse help; log-only progress invocation; service template path rendering and `make -n install-service`. No install/reload/start/stop/authentication/archive discovery/data export was executed. The log-only progress CLI's handling of `--help` was observed and its docs corrected, not described as argparse support.

Full final CI results are recorded with the serialized publication manifest. The initial full run preceded the last checker/cache regression; final CI is rerun on the frozen checker/tests. Passing unit/static tests does not verify native entitlement, data coverage, automations, profitability or promotion.

## Related projects and remaining limits

Alphas02 and alphas3 receive size-appropriate README/design/inventory revisions and the same offline docs checker. Their course/reference content retains provenance. WQ-Brain, worldquant-miner and WorldQuant_alpha101_code remain upstream/reference forks in this portfolio scope; their docs are not rewritten as an independently deployed system.

No external links or native platform thresholds were refreshed to validate prose. Source metadata and dated source claims are clearly distinguished from current guarantees. Serial publication must verify the exact committed tree and terminal hosted CI at its published SHA; local validation alone is not hosted acceptance. This documentation phase does not change package versions or activate services.

## Final local results

Frozen-checker `CARGO_BUILD_JOBS=2 make ci` exited 0 on Python3.12.14:
**1629 Python tests passed, 16 corpus checks skipped, 22 Rust tests passed**;
format, Ruff, mypy (267 source files), Bandit and Vulture passed. Log:
`/tmp/brain-work-docs-final-ci-20261107.log`. The final prose-only results update
was rechecked with docs-check and staged whitespace verification.

Alphas02: four owned Markdown documents, three unchanged notebooks/82 code
cells, four passing unit tests. Alphas3: five owned Markdown documents,
15 tracked Python files parsed, six passing unit tests. Hosted matrix runs at
the published final SHAs remain the coordinator's acceptance step; these are
local results, not a claim about a future hosted run.

## Native follow-up and final prose correction

Native local-only commit `962fba1da43cb2aafbef207bdc240d8e7aac7a4e` commits
17 maintained Markdown guides plus their reviewed documentation prerequisites,
without staging source/runtime files. Inline local link/anchor checks passed
for all17; the native index was empty before/after this scoped commit.
Private active handoff/policy/owner ledgers were outside the write/staging list.
The native quota helper has no identified core/runner dispatch caller in this
audit; native guides now distinguish helper existence from enforced policy.
Native unguarded test behavior and inherited code-gate findings are documented
rather than relaxed or retested as part of docs-only work. This private native
commit is not a publication candidate.

The final public operations sentence now says an *explicit* user pause takes
precedence, rather than implying a current pause. This prose-only follow-up
was rechecked with docs-check and whitespace checks; the tested source/checker
and workflows are unchanged from the full green docs CI tree.
