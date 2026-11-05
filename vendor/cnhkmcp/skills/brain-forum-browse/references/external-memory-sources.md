# External Memory Sources

Phase 0a harvests **read-only** memory from the host AI environment. Write results only to `outputs/workspace/external_memory_snapshot.json`.

## Priority stack (P0–P5)

| P | Source | Location |
|---|--------|----------|
| P0 | Skill action ledger | `outputs/workspace/action_ledger.json` |
| P1 | Skill experience | `outputs/workspace/personal_experience_memory.md` |
| P2 | Project memory files | See host table below |
| P3 | User-level memory | `~/.claude/CLAUDE.md`, etc. |
| P4 | Session / host memories; **AI tool chat history** (Cursor/Claude/Kimi research 对话) |
| P5 | BRAIN MCP facts | `get_user_alphas`, etc. |

Conflict: forum facts → P0; alpha facts → P5; preferences P1 > P2 > P3.

## Host scan paths

Respect `agent_profile.preferred_host` for scan order.

### cursor

- `.cursor/rules/*.mdc`
- `AGENTS.md`, `.cursorrules`
- Session: user rules, @ docs (agent extracts manually)

### claude_code

- Project `CLAUDE.md`, `MEMORY.md`
- `~/.claude/CLAUDE.md`
- Claude project memory from context

### kimi

- `AGENTS.md`, project `memory/`

### codex

- `AGENTS.md`, `.codex/`, `instructions.md`

### windsurf

- `.windsurfrules`, `AGENTS.md`

### copilot

- `.github/copilot-instructions.md`

### generic

- `todo.md`, README research sections

### AI tool chat history (P4 — unique contribution fuel)

When building **E1 personal experience**, agent may cite **prior research conversations** on this machine:

| Source | When to use |
|--------|-------------|
| **Current session chat** | User/assistant discussed sim, alpha, dataset this thread — tag `P4 session` |
| **Cursor agent-transcripts** | Project `.cursor/…/agent-transcripts/*.jsonl` — specific past debugging/research turns |
| **Claude / Kimi project memory** | MEMORY.md, exported notes from same BRAIN research topic |

Rules: only cite **what was actually said or simulated in that chat**; date/topic in `evidence_sources`; never invent metrics from memory of a chat. See [unique-contribution.md](unique-contribution.md).

## Do NOT scan

- `.env`, `user_config.json`, files containing passwords/tokens

## Harvest procedure

```
1. Find project root from skill dir (walk up for .git or CLAUDE.md)
2. Glob/read paths that exist
3. Extract BRAIN-related bullets: region, dataset, workflow, submission habits
4. Write external_memory_snapshot.json:
   { harvested_at, mode, sources: [{path, host, bullets}], merged_bullets }
5. Update forum_findings.md Memory Sources table
6. If zero files: mode=session-only; extract from current chat
```

## Write-back policy

After Act, update **skill workspace only**. Do not auto-edit `CLAUDE.md` or Cursor rules unless user explicitly asks.
