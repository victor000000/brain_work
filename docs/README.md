# Documentation index

These guides describe the published 1.0.1 source. Host state and account evidence remain private and time-dependent. Current code is authoritative for defaults; native metadata/verdicts are authoritative for platform entitlement and acceptance.

| Guide | Contract |
|---|---|
| [Setup](SETUP.md) | Bootstrap, offline validation and optional native service installation |
| [Architecture](../ARCHITECTURE.md) | Modules, data flow, ownership and design limits |
| [Configuration](CONFIGURATION.md) | Credentials, environment controls and defaults |
| [Operations](OPERATIONS.md) | Safe inspection, pause/resume, request ownership and recovery |
| [Data](DATA.md) | Tables, state semantics, exports and provenance |
| [Research](RESEARCH.md) | Scope, finite studies, native checks and promotion evidence |
| [Development](DEVELOPMENT.md) | Tests, CI, parser build and contribution checks |
| [Troubleshooting](TROUBLESHOOTING.md) | Symptoms, evidence and safe next actions |
| [Email archive](EMAIL_RESEARCH.md) | Optional external integration and archive contract |
| [Credential migration](CREDENTIAL_MIGRATION.md) | Exclusive backup-first removal and byte-verification limits |
| [Tools](../tools/README.md) | CLI effects and prerequisites |
| [Publication](../PUBLICATION.md) | Public source versus private deployment state |

## Dated design and reference material

[November 7 Expert design](EXPERT_PV_OPTIONS_DESIGN_20261107.md) is a proposal with retained account observations, not an implementation or live status report. Its local evidence links identify private records that are intentionally omitted from this public source.

[Platform rules](../BRAIN_RULES.md), [field rules](../BRAIN_FIELD_RULES.md), [constraints](../BRAIN_CONSTRAINTS.md), [submission details](../BRAIN_SUBMIT_RULES.md), [template catalog](TEMPLATE_CATALOG.md), [forum extraction](forum-templates.md) and [cnhkmcp extraction](cnhkmcp-templates.md) preserve dated observations. Their historical counts and claims are not current guarantees. Use canonical guides for current procedures and verify platform rules before research spending.

[Vendor provenance](../vendor/README.md) identifies third-party source; vendored manuals/skills describe upstream projects and do not authorize actions here. Private deployment handoffs, dated research/status archives, provider requirements and raw email/forum evidence are inventoried separately in the documentation audit, not exported to make public links work.

## Documentation maintenance

Run `make docs-check` after changes. It validates owned Markdown inline local links and heading fragments, excluding external URLs and third-party manuals. It does not validate external availability, private archives, runtime authorization or native account rules. The audit report records precise inventory and exclusions.
