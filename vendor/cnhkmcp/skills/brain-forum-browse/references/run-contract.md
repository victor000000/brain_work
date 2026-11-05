# Run Contract（标准 write 路径）

**何时需要 Run Contract：** 本轮 MCP write **未**满足 [auto-send-e1.md](auto-send-e1.md) 全部条件时 — 包括：

- 多条 write、upvote、Linker、含 E2/E3、含建议/推断/提问
- 单条但 agent 对 E1 纯事实复述**无把握**（`auto_send_certification: fallback_to_contract`）

**可跳过 Run Contract（窄例外）：** 单条跟评或新帖（**仅 1 条 write**），**E1-only、零推断、自检 PASS** — 见 [auto-send-e1.md](auto-send-e1.md)。write 后直接汇报，不等 `同意执行`。

**explore / contribute 均仍须本轮有贡献**；auto-send 只是省略合同门，不省略 write。

## Forbidden UX（所有模式）

- 「接下来可以帮你做这些事…你想先做哪一项？」
- 让用户从深读/跟评/点赞/搜帖里挑顺序
- 浏览后零 write 直接结束
- **把不符合 A1–A8 的草稿强行 auto-send** 以跳过审查

**Run Contract 范围：** 仅论坛 MCP write（搜/读/评/赞/帖）。**Follow-on impulses**（研究、探索、其他 skill 提案）写在 `forum_stroll_notes.md`，**不进合同、不需 同意执行** — 见 [follow-on-impulses.md](follow-on-impulses.md).

---

## 流程

```
Block 1 — Context: Phase 0–1 (+ contribute 时 Phase 2–5 Recon)
Block 1.5a — Auto-send E1? 若 A1–A8 全过 → MD→HTML → 聊天贴 HTML 预览 → Phase 9（单条）
Block 1.5b — Draft + Phase 7.5: evidence + adversarial subagent（标准路径）
Block 2 — Run Contract: Phase 1.5 — STOP for 同意执行 / 修改 / 取消 (PASS drafts only)
Block 3 — Execute: Phase 6–9 — auto after 同意执行, no per-item menu
```

**explore stroll：** 单条 E1 auto-send 可走 Block 1.5a；其余 Block 1.5b–3 不可跳过。

---

## Run Contract 内容

基于 memory +（contribute：gap_list + session_l1；explore：stroll contribution plan）；**write 区块不可为空**（满足最低贡献条）。

### Minimum contribution checklist（explore）

- [ ] ≥1 evidence-backed comment **or** new post (E1/E2/E3 per claim)
- [ ] **or** user-approved comment + upvote combo documented in contract
- [ ] Each draft: `evidence_sources[]` + `adversarial_review_status: pass`
- [ ] If weak opinion: linker-style minimal value (link/index pointer) with E2 basis
- [ ] If nothing merited: **why** documented in stroll notes + fallback linker action attempted

必填:

- 依据（memory + history + 为何此刻写）
- 搜/读/评/赞/帖 计划 + **完整中文草稿**
- **每条 comment/post 草稿**须含：
  - `evidence_sources[]` — 每条主张的可追溯来源（E1/E2/E3），见 [evidence-and-review.md](evidence-and-review.md)
  - `adversarial_review_status: pass` — Phase 7.5 子 agent 对抗审查已通过；`revised` 须注明修改项并已 re-review
- 结尾：`同意执行` / `修改：…` / `取消`

**Gate:** 未通过对抗审查的草稿 **不得** 写入合同或呈现给用户。主 agent 须在 Phase 7.5 完成 review → 修订 → PASS 后再进入 Phase 1.5。

Curator：**contribute** 模式合同默认含 ≥1 upvote（无合格则说明）。**explore** — 推荐合同含 ≥1 upvote when merited；不强制块但须在 checklist 中考虑。

---

## Config

- `default_run_mode`: `"explore"` — stroll-with-mandatory-contribution
- `consent_mode`: `"upfront_batch"` — 默认；**窄例外**见 `auto_send_e1` + [auto-send-e1.md](auto-send-e1.md)

Legacy `per_item` if user explicitly asks.
