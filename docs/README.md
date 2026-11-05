# Documentation index

Read [the project overview](../README.md), then the guide for the task. These pages describe the implementation inspected on October 21, 2026. Runtime/account numbers are dated observations, not evergreen guarantees.

## Maintained guides

For the next agent pursuing Expert, start with the October28
[Expert execution plan](EXPERT_EXECUTION_PLAN.md). It includes a fresh account
snapshot, pending-owner reconciliation, prioritized research and a copyable handoff.

| Guide | Contents |
|---|---|
| [Setup](SETUP.md) | Native Python environment, dependencies and user service |
| [Operations](OPERATIONS.md) | Ownership, lifecycle, logging, quotas, restart and long-pause recovery |
| [Configuration](CONFIGURATION.md) | Environment settings, credentials, paths and source defaults |
| [Architecture](../ARCHITECTURE.md) | Layer map and lifecycle |
| [Data](DATA.md) | Storage contract, table map, provenance, WAL and Parquet |
| [Research](RESEARCH.md) | Scope, templates, probes, validation and Expert milestones |
| [Development](DEVELOPMENT.md) | Tests, CI, parser development and documentation maintenance |
| [Troubleshooting](TROUBLESHOOTING.md) | Evidence-driven diagnosis and known implementation limits |
| [Email research](EMAIL_RESEARCH.md) | Inbox/Spam routine, all-category archive, deduplication and schedule |
| [Current state](CURRENT_STATE.md) | Pause status, saved outputs and pending parent IDs |
| [Tools](../tools/README.md) | Commands grouped by effect and DB ownership |
| [TODO](../TODO.md) | Current incomplete work and unresolved decisions |
| [Agent instructions](../CLAUDE.md) | Minimal operational constraints for future work |

## Specialized references

- [Platform behavior](../BRAIN_RULES.md), [field and operator rules](../BRAIN_FIELD_RULES.md), [region constraints](../BRAIN_CONSTRAINTS.md), and [submission rules](../BRAIN_SUBMIT_RULES.md). Check their dates and native evidence before using a threshold or availability claim.
- [Template catalog](TEMPLATE_CATALOG.md), [forum templates](forum-templates.md), and [cnhkmcp templates](cnhkmcp-templates.md). Catalog membership does not establish native availability or acceptance.
- [Current US/CN provider handoff](data_requirements/CURRENT_BRAIN_PV_OPTIONS_REQUIREMENTS.md), including detailed per-field descriptions and calculated-value requirements.
- [Saved email contents and index](forum/brain_email_ideas_20261021/README.md).
- [Vendor notes](../vendor/README.md).
- `docs/research/`, `docs/status/` and `docs/superpowers/` retain dated research, design and status artifacts. They do not override the latest user instructions or current operations guide.
- [Historical operating notes](archive/README.md).

## Sources of truth

1. Latest explicit user authorization and pause state.
2. Current code and actual service/native API state.
3. Raw native responses, receipts and immutable plan hashes.
4. Current guides and dated handoff.
5. Historical notes and third-party claims.

Keep changing campaign results in dated artifacts. Update the handoff when work pauses or resumes; do not append daily logs to every guide.
