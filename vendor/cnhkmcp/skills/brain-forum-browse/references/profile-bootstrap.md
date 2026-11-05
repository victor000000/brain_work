# Profile Bootstrap

First run when `data/agent_profile.json` missing.

## Explore-first（默认逛论坛触发）

若用户首句是「逛一逛论坛 / 看看论坛」等 **explore** 触发，**不要**阻塞 MCP：

1. `python scripts/init_workspace.py --new-run` — **必做**
2. `get_user_alphas`（Phase 0b）— **必做**
3. **Defer L2 interview** — 从 P5 / P0–P4 / 聊天推断 specialty；`agent_profile.json` 可暂缺或最小 `{}`
4. 用户明确 **contribute / 填空白** 或第二轮再跑 `init_profile.py`

## Contribute-first 或用户愿意配置时

Ask user (L2 only):

1. Primary specialties — pick 1–3 from: PPAC, VF, beginner, correlation, SuperAlpha, templates, region, dataset
2. Optional `l2_params`: region (USA/EUR/…), dataset id
3. Optional `preferred_host`: cursor | claude_code | kimi | codex | windsurf | copilot | generic

## Do NOT ask

- L1 role (commenter/author/linker) — chosen each run via contribution plan / Role Pick
- Whether to be curator on explore — **explore 仅推荐**；contribute 合同内必考虑

## Run (when profile wanted)

```bash
python scripts/init_profile.py
python scripts/validate_profile.py
python scripts/init_workspace.py --new-run
```

Optional (stale host memory):

```bash
python scripts/harvest_external_memory.py --write
```

## Output

`data/agent_profile.json` matching [agent_profile.schema.json](../data/agent_profile.schema.json).

## role_history

Appended after each Act with `{at, l1, gap_type}`. Keep last 20 entries.
