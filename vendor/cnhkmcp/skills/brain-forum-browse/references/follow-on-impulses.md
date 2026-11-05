# Follow-on Impulses（逛后延伸 — 非论坛 write）

逛论坛时，高质量帖/跟评/公告常会触发**与本轮 forum write 并行的研究或探索想法**。  
本文件定义如何**记录并汇报**这些想法 — **不是**替代必贡献，**不是**自动开新 pipeline。

---

## 定位（先读）

| | 论坛贡献（必做） | Follow-on impulses（建议性） |
|--|------------------|------------------------------|
| 交付物 | Run Contract → MCP write | `forum_stroll_notes.md` 本节 + 聊天摘要 |
| 用户门控 | **同意执行** 后发帖/跟评/点赞 | **不自动执行**；仅提案，等用户另开口或 invoke 其他 skill |
| 证据 | E1/E2/E3 + Phase 7.5 对抗审查 | 须标注依据 tier；未验证假设标 **待验证** |
| 范围 | 中文论坛 MCP write | 研究、sim、数据集探索、Theme 对齐等 |

**禁止：** 用一长串 follow-on 清单代替本轮贡献；把 follow-on 包装成「你想先做哪一项？」菜单；未读 MCP 就声称官方在呼吁某类 Alpha。

---

## 什么情况下会产生 follow-on

Agent 在深读或逛读时，若出现下列**类型**信号（以下为**模式说明**，非固定模板），可在贡献计划之外记录 0–3 条 follow-on：

### A — 技术帖触发的研究 hook

**模式：** 帖/评给出可复现细节（算子组合、性能对比、实现取舍、IS burn-in 等），且与 P1/P5 或当前 research 焦点有交集。

**Follow-on 示例形态（抽象）：**

- 「可复现楼主方案 B 的 lookback 设定，对比 warm-start vs 冷启动对前 N 天 coverage/turnover 的影响」→ 待验证 sim，非论坛断言  
- 「该 field 的 coverage 尚未摸清，适合先做 datafield 探索再决定是否写 Alpha」→ handoff 数据集探索 skill  

**对抗性约束：** 不得把 follow-on 里的未 sim 结论写进 forum 跟评；forum 里只写**已有 E1/E2/E3 支撑**的内容。follow-on 可写「若验证 X，再考虑 Y」。

### B — 官方 / Theme / 活动信号

**模式：** 帖内引用或 MCP `get_messages` / `get_events` 出现 Theme、Multiplier、顾问功能、operator 计数规则变更等。

**Follow-on 示例形态：**

- 「公告要求某 region/delay 的 Y 类 Alpha → 对照 P5 近期提交缺口，是否值得排一轮 makeSomeGem」  
- 「新 operator 政策只影响计数口径 → 研究 priority 应放在信号质量而非堆 operator 数」  

**对抗性约束：** Theme/公告主张 **必须** `[E2: get_messages …]` 或 `[E2: get_events …]`；禁止「平台最近在推 X」而无 MCP 出处。

### C — 开放问题 / 知识空白

**模式：** 高质量讨论留下未答子问题（如某实现细节是否影响 IS 前段），且**不适合**或无 E1/E2/E3 在本轮跟评里硬答。

**Follow-on：** 记入待研究问题；可选在 forum 贡献里**只问**有 E2 依据的 narrow question（算 contribution，不算 follow-on 重复）。

### D — 与已有 skill 的自然 handoff

**模式：** 逛论坛发现的需求，本 skill **不应**在 Phase 6–9 之外擅自执行（batch sim、拉 dataset、改模板等）。

**Follow-on：** 标明建议 skill + 一句启动条件（用户说什么话 / 什么前提满足再做）。

---

## 记录格式（`forum_stroll_notes.md`）

每轮 **0–3 条**（无则写「本轮无延伸」）。每条：

```yaml
- id: F1
  spark: "E2 MCP read_full_forum_post post_id=… / comment by @…"  # 触发源，必填
  impulse_type: research_hook | theme_alignment | open_question | skill_handoff
  one_liner: "一句话描述想法（中文）"
  hypothesis: "待验证 | 已有 E1 …"  # 未 sim/未读数据的一律 待验证
  suggested_next: "用户若感兴趣，可 …"  # 非命令式
  handoff_skill: brain-makeSomeGem | brain-datafield-exploration-general | … | none
  priority: now | later | maybe
  overlaps_contribution: true | false  # true = 与本轮跟评主题相关但延伸超出 forum 范围
```

**汇报语气（聊天）：** 贡献 Run Contract 与执行结果之后，用 **「延伸想法（可选，不自动做）」** 小节列出 1–3 条 one_liner + suggested_next。**不要**编号菜单让用户选「做 A 还是 B」。

---

## Skill handoff 表（仅提案，不自动 invoke）

| 想法类型 | 建议 skill | 典型用户触发语 |
|----------|------------|----------------|
| 摸清 field / dataset | `brain-datafield-exploration-general`, `brain-dataset-exploration-general` | 「帮我查这个 field」「audit 这个 dataset」 |
| 产表达式 / GEM | `brain-makeSomeGem` | 「按这个想法产 Alpha」「region=… dataset=…」 |
| 模板增强 | `brain-enhance-template` | 「cross 增强」「模板融合」 |
| 批量 sim | `brain-simAlphasinBatch-and-track` | 「批量模拟」「断点续传」 |
| Feature 概念 | `brain-data-feature-engineering` | 「对这个 dataset 做 feature 想法」 |
| 改现有 Alpha | `brain-improve-alpha-performance` | 「提升这个 alpha」「修 submission test」 |
| 日内研究循环 | `brain-deepExplore` | 「持续探索」「今天 research loop」 |
| Alpha 提交审查 | `brain-alpha-judge` | 「提交前审查」（**非** live 论坛） |

本 skill **禁止**在 follow-on 名义下直接调用上表 skill 的 write/sim API，除非用户在**同一会话或新消息**中明确请求。

---

## 与贡献计划的关系

1. **顺序：** 先定 contribution plan → Phase 7.5 → Run Contract → 执行 write → **再**整理 follow-on（可在逛读过程中草稿，但最终写入 notes 不替代贡献节）。  
2. **同帖双轨：** 对同一帖既可跟评（E1/E2 已就绪部分），又可在 follow-on 记「尚待 sim 的延伸」— 跟评里不得写待验证结论。  
3. **contribute 模式：** formal gap 驱动的 write 仍优先；follow-on 来自 Recon/深读同样适用，写入 `forum_findings.md` 末尾 **Follow-on impulses** 小节（结构同 notes）。

---

## 对抗性检查清单（Agent 自检）

- [ ] 本轮必贡献已满足，follow-on 未用来跳过 write  
- [ ] ≤3 条，每条有 spark（post_id 或 MCP 公告指针）  
- [ ] 无「平台一定想要 X Alpha」类无 E2 断言  
- [ ] hypothesis=待验证 的项未 sneak 进 forum 草稿  
- [ ] 未自动启动 sim / makeSomeGem / batch  
- [ ] 聊天汇报未变成 A/B/C 行动菜单  
- [ ] handoff_skill 名称正确，未把 forum browse 扩 scope 成全能 research orchestrator  

---

## 持久化（可选）

高价值、跨轮复用的 hook 可在用户同意后 append 到 `outputs/workspace/personal_experience_memory.md`（§Research backlog），**不**写入 action_ledger 的 contributed 字段。
