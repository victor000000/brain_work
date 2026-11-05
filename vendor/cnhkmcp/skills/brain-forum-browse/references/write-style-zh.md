# Write Style (简体中文)

All `create_forum_post` and `create_forum_comment` content **must be Simplified Chinese**.

**Forbidden:** 空话、重复他人、重复自己过往 snippet；见 [unique-contribution.md](references/unique-contribution.md).

**Hard rule — evidence-backed only:** Every factual claim, metric, recommendation, or causal statement must trace to ≥1 evidence tier (E1 personal experience, E2 MCP data, E3 named paper). See [evidence-and-review.md](evidence-and-review.md).

**Forbidden:** 「我觉得可能」「应该会」「研究表明」（无具体论文）、编造 VF/名次/提交数、未 MCP 读取就复述帖文。

---

## Forum format: HTML only at submit（必读）

WorldQuant BRAIN 中文论坛编辑器是 **HTML 富文本**，**不是 Markdown 渲染器**。

| 阶段 | 格式 |
|------|------|
| 草稿 / Run Contract / 笔记 | 可用 **Markdown** 便于撰写与 diff |
| **`create_forum_comment` / `create_forum_post` 的 `body` / `details` 参数** | **必须是论坛原生 HTML** — 提交前完成 MD→HTML 转换 |

**禁止：** 把 `#`、`**bold**`、`` `code` ``、`- list`、`` ``` `` 等 Markdown 原样传给 MCP write API（会显示为乱码纯文本）。

### Markdown → HTML 对照（提交用）

| Markdown 草稿 | 提交 HTML |
|---------------|-----------|
| 段落 | `<p>…</p>` |
| 换行（段内） | `<br>`（少用；优先分段 `<p>`） |
| `**粗体**` | `<strong>粗体</strong>` |
| `*斜体*` | `<em>斜体</em>` |
| `` `alpha_expr` `` | `<code>alpha_expr</code>` |
| 代码块 / 表达式块 | `<pre><code>…</code></pre>` |
| `- item` 无序列表 | `<ul><li>item</li></ul>` |
| `1. item` 有序列表 | `<ol><li>item</li></ol>` |
| `[文字](url)` | `<a href="url" rel="noopener noreferrer">文字</a>` |
| `> 引用` | `<blockquote><p>…</p></blockquote>` |
| `## 小标题` | `<h3>小标题</h3>`（跟评慎用；新帖可用 `<h2>`/`<h3>`） |

### 论坛原生 HTML 约定

- **表达式与设置：** 用 `<pre><code>` 或 `<p><code>`，保留括号与逗号，不依赖 Markdown fence。
- **链接：** 仅 `https://` 绝对 URL；`rel="noopener noreferrer"` 推荐。
- **不用：** 内联 `style=`、`<script>`、`<iframe>`、表格除非必要（优先列表）。
- **证据 tag `[E1: …]`：** 仅留在 Run Contract / 笔记；**提交 HTML 正文中删除**或改为自然中文（audit trail 在 workspace，不进帖文）。
- **预览：** 转换后目视检查 — 无裸露 `**`、`` ` ``、`#`、未闭合标签。

### MCP 调用示例

```json
{
  "tool": "create_forum_comment",
  "arguments": {
    "post_id": "31002256151831",
    "body": "<p>同帖 delay=1 USA，我 alpha <code>abc123</code> IS Sharpe 1.05（刚查平台）。</p><p>设置：TOP3000，neutralization=SUBINDUSTRY。</p>"
  }
}
```

新帖 `details` 字段同样为 HTML；`title` 为**纯文本**（不含 HTML/Markdown）。

**Phase 9 顺序：** 定稿 → **Markdown 转 HTML**（推荐 `python scripts/md_to_forum_html.py`）→ `create_forum_*`（`body`/`details` 仅 HTML）→ 确认响应。

### 转换脚本

```bash
python scripts/md_to_forum_html.py --input draft.md --output submit.html
python scripts/md_to_forum_html.py --text "**粗体** 与 `code`"
```

Agent 仍须目视检查：无裸露 Markdown 标记、标签闭合、证据 tag 已剥离。

---

## Comment structure

1. 一句承接楼主问题（不空洞表扬）— 承接点须来自 E2 MCP 读帖
2. **≥1 条独特细节** — 线程里尚未覆盖的：你的 alpha 数字 / 本机 AI 对话里真实 sim 踩坑 / 你的 region-dataset-operator 组合（E1/E2/E3）
3. 1–3 条可执行细节（operator / region / dataset / 测试名）— 每条标注 E1/E2/E3
4. 个人经验一句须带来源（含 `[E1: P4 Cursor chat …]` 当引用历史对话）
5. 禁止纯「同意」「+1」「感谢分享」、禁止复述神评而不加新信息

## Post structure

- 标题：`【L2标签】具体场景 — 要点`（含 region/dataset/operator 至少一项）
- 开篇：问题/背景 2–3 句
- 正文：步骤或清单，可含代码块表达式 — **提交时为 HTML**（见上文 Forum format）
- 结尾：开放问题或邀请补充（非营销）

## Tone

- 实操向、克制、不吹嘘 VF/名次
- 不伪造 submission 记录 — 数字只来自 E1/E2
- 跟官方公告：只写 uncovered points（见 content-diversity.md）
- 外部论文须点名或 arXiv ID（E3），禁止模糊引用

## Evidence citation (Run Contract)

Per draft in Run Contract, list `evidence_sources[]`:

```yaml
- tier: E1 | E2 | E3
  pointer: "P5 get_user_alphas alpha_id=…" | "MCP read_full_forum_post post_id=…" | "arXiv:…"
  supports: "哪条主张"
```

Drafting may use inline `[E1: …]` tags; final Chinese body reads naturally but contract keeps audit trail.

**Run Contract 建议双栏：** `草稿（Markdown，可选）` + **`提交 HTML（Phase 9 实际 body/details）`** — 用户 `同意执行` 前应看到 HTML 版。

## Adversarial review (before Run Contract)

Each comment/post draft → subagent review per [evidence-and-review.md](evidence-and-review.md). Only `adversarial_review_status: pass` drafts go to user.

## Curator comment quality bar

Reference [brain-alpha-judge](../../brain-alpha-judge/SKILL.md) rubric **read-only** for what "good" looks like — do not invoke judge MCP at runtime.

## Confirm gate

Default **`upfront_batch`**: full Chinese drafts live in **Run Contract** (Phase 1.5). User replies **`同意执行`** once; then Phase 6–9 run without per-item prompts.

Legacy **`per_item`**: only if user explicitly asks for step-by-step confirm.

Never end Recon with an action menu — see [run-contract.md](run-contract.md).

## MCP mapping

| Draft type | Tool | Args |
|------------|------|------|
| 跟评 | `create_forum_comment` | `post_id`, `body` (**HTML**) |
| 新帖 | `create_forum_post` | `topic_id=12913416465431`, `title` (plain text), `details` (**HTML**) |

Never call write tools in Phase 8 — only Phase 9 after confirm. Phase 7.5 adversarial review runs **before** Phase 1.5 Run Contract. See [mcp-by-phase.md](mcp-by-phase.md).
