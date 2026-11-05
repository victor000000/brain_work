---
name: wq-brain-alpha-optimization-v1
description: >-
  Optimize an existing WorldQuant BRAIN alpha under strict local validation,
  8-candidate batch generation, and low-correlation submission rules. Use when
  the user asks to improve a BRAIN alpha ID, keep the core fields frozen,
  generate 8 variants per round, validate expressions before create_multiSim,
  reduce PROD correlation below 0.7, or pass all checks including
  IS_LADDER_SHARPE.
user-invocable: true
---

# WQ BRAIN Alpha Optimization V1

Use this skill for end-to-end optimization of an existing WorldQuant BRAIN alpha with strict preflight validation, structured iteration, and forced low-correlation checks.

## Hard Rules

1. Freeze the baseline alpha's core fields and dataset. Do not replace them in later rounds.
2. Before any simulation, every candidate must pass local validation.
3. Each round must contain exactly 8 candidate expressions.
4. Platform `operatorCount` is the final judge. Any candidate above 8 is invalid.
5. In Stage A, pure fine-tuning is forbidden. Use structural upgrades only.
6. Any candidate with zero FAIL items must immediately go through submission correlation checks.
7. After `create_multiSim` finishes, append the current batch results to the requested text file immediately using UTF-8 append mode.
8. If validation or simulation fails, fix the exact error point. Do not simplify the expression by removing its core logic just to make it pass.

## Required Workflow

1. Confirm valid platform settings with the WorldQuant BRAIN MCP tools.
2. Read the baseline alpha and freeze its core data fields.
3. Plan the 8 roles first, then write expressions under the theme quota and common-operator limits.
4. Run an operator preflight against the local operator library before validation.
5. Run local expression validation and repair until clean.
6. Backtest the 8 validated expressions with `create_multiSim`.
7. If the batch output is truncated, fetch missing details individually.
8. Append the 8 results to the target results file right after the backtest.
9. Diagnose negative-signal flips, `operatorCount` overflow, FAIL reasons, and correlation before the next round.

## Validation Layer

- Primary: use the local `validate_expression` capability when it is exposed in the current project.
- Companion syntax checker: reuse the existing [expression verifier skill](../alpha-expression-verifier/SKILL.md).
- Treat syntax validation and operator-signature validation as hard gates before any platform request.

## Progressive Docs

- Full rules, theme quotas, step-by-step flow, and file append contract: [reference.md](reference.md)
- Example prompts, output format, and the `LLbaqEqa` optimization case: [examples.md](examples.md)

## Expected Outcome

Keep iterating in 8-expression rounds until at least one candidate satisfies all of the following:

- Sharpe > 1.58
- Fitness > 1.0
- Turnover between 1% and 40%
- All platform checks PASS, including `IS_LADDER_SHARPE`
- `PROD correlation < 0.7`