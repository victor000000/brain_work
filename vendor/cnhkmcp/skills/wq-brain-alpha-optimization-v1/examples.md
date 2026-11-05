# WQ BRAIN Alpha Optimization V1 Examples

## Example 1: Direct Optimization Request

User prompt:

```text
你必须严格按照 @Skill-ImproveTheme-V1.md 中的规则工作，使用 worldquant-brain-platform mcp 工具。
对 JPN alpha id 为 LLbaqEqa 的表达式进行优化。
region=JPN, delay=1，目标是所有指标都 PASS，prod correlation < 0.7，IS_LADDER_SHARPE 也要通过。
在使用 create_multiSim 完成回撤验证后，必须立即将本轮 8 个 Alpha 的核心结果追加写入 LLbaqEqa_optimization_results.txt。
```

Expected behavior:

1. read the baseline alpha and freeze its core fields
2. confirm valid JPN settings
3. plan exactly 8 candidates under Stage A or Stage B rules
4. run operator preflight against the local operator library
5. run local validation before simulation
6. run the 8-expression batch simulation
7. append the batch summary to `LLbaqEqa_optimization_results.txt` immediately
8. run submission checks only for zero-FAIL candidates

## Example 2: Stage A Structural Round

User prompt:

```text
帮我继续优化这个 BRAIN alpha，但目前 Sharpe 只有 1.1，Fitness 只有 0.7，不要做纯调参。
```

Expected behavior:

- classify the next round as Stage A
- forbid pure parameter-only edits
- use structural themes such as denoising, trade freeze, orthogonalization, correlation structure, or turnover control
- keep the batch size at 8
- validate every expression locally before simulation

## Example 3: Negative Signal Flip

User prompt:

```text
上一轮里有两个表达式 Sharpe 很差但不像噪声，继续做下一轮。
```

Expected behavior:

- inspect the previous round for candidates with `Sharpe <= -1.20` and `Fitness <= -0.50`
- tag them as `CAND_NEG`
- include at least 2 flipped versions in the next 8-expression round
- still obey operator-count, theme, and validation gates

## Example 4: Local Validation Contract

User prompt:

```text
先不要急着回测，先把这 8 条表达式做严格校验。
```

Expected behavior:

- run the local `validate_expression` path when available
- also reuse the [expression verifier skill](../alpha-expression-verifier/SKILL.md) when a syntax-level cross-check is useful
- fix only the exact syntax, signature, keyword, comma, or parenthesis errors
- do not simplify the strategy logic just to obtain a green validation result

## Example 5: Required Batch Log Format

Suggested appended block:

```text
[2026-03-09 14:32:10] baseline=LLbaqEqa round=3 region=JPN delay=1
slot=1 alpha_id=AAA Sharpe=1.62 Fitness=1.08 Turnover=0.18 FAIL=none PROD=0.64
slot=2 alpha_id=BBB Sharpe=1.31 Fitness=0.92 Turnover=0.11 FAIL=IS_LADDER_SHARPE
slot=3 alpha_id=CCC Sharpe=-1.28 Fitness=-0.58 Turnover=0.14 FAIL=none tag=CAND_NEG
slot=4 alpha_id=DDD Sharpe=0.97 Fitness=0.61 Turnover=0.43 FAIL=Turnover
slot=5 alpha_id=EEE Sharpe=1.55 Fitness=0.98 Turnover=0.16 FAIL=Sub-universe
slot=6 alpha_id=FFF Sharpe=1.43 Fitness=0.94 Turnover=0.21 FAIL=none PROD=0.78
slot=7 alpha_id=GGG Sharpe=1.09 Fitness=0.76 Turnover=0.10 FAIL=Weight
slot=8 alpha_id=HHH Sharpe=1.24 Fitness=0.88 Turnover=0.15 FAIL=none
next_actions=flip slot3, decorrelate slot6, compress operators for slot4
```

The exact text layout may differ, but it must be appended immediately after each batch and preserve the 8-slot round history.