# WQ BRAIN Alpha Optimization V1 Reference

This reference defines the operating rules for optimizing an existing WorldQuant BRAIN alpha without wasting simulation budget.

## 1. Goal

Generate, validate, simulate, diagnose, and iterate in fixed 8-expression batches until a candidate becomes submission-ready while staying below the production correlation ceiling.

## 2. Definition Of Done

A candidate is considered done only when all conditions below are true:

- Sharpe > 1.58
- Fitness > 1.0
- Turnover is between 1% and 40%
- Max single-stock weight is below 10%
- Sub-universe Sharpe passes under the platform's own checks
- `IS_LADDER_SHARPE` passes
- All platform checks show PASS with zero FAIL items
- `get_submission_check` confirms `PROD correlation < 0.7`

If `PROD correlation >= 0.7`, the candidate is not done even if every other metric passes.

## 3. Inputs

Required inputs:

- `baseline_alpha_id`
- platform settings: `region`, `universe`, `delay`, `neutralization`, `language`
- local operator library such as `operators.json` or the repository's canonical operator definition file

Optional inputs:

- preferred stage hint: `Stage A` or `Stage B`
- known failure history such as `operatorCount`, `weight`, `sub-universe`, `correlation`, `unit`, `warning`
- explicit output file name for round logging

## 4. Standard Outputs

Each round should produce these logical artifacts in the response or notes:

- `batch_plan`: the 8 expressions, their role, theme pair, and rough operator count
- `preflight_report`: operator existence and signature checks against the local operator library
- `local_validation_report`: validation status and exact repair record
- `backtest_summary`: alpha IDs, key metrics, and FAIL items
- `next_batch_actions`: what to flip, compress, denoise, or de-correlate next

## 5. Tooling

Use WorldQuant BRAIN platform tools when available:

- `get_platform_setting_options`
- `get_alpha_details`
- `create_multiSim` or the platform-equivalent multi-simulation tool
- `get_user_alphas`
- `get_submission_check`
- `get_SimError_detail` or the platform-equivalent simulation error tool

Use local validation before any simulation request:

- project `validate_expression` or `validate_expressions` entrypoint if exposed
- [expression verifier skill](../alpha-expression-verifier/SKILL.md) for syntax and argument-shape validation

## 6. Global Constraints

### 6.1 Core Field Freeze

Read the baseline expression first and freeze its core fields or dataset family. Later candidates may transform, denoise, neutralize, combine, or invert those fields, but must not replace the core source with unrelated fields.

### 6.2 Operator Count Ceiling

Every expression must stay within platform `operatorCount <= 8`.

Self-estimation is only a rough gate before simulation:

- count each distinct function name once
- count `+`, `-`, `*`, `/` as operators when they appear directly
- fields, constants, and parentheses do not count
- if function forms such as `add` or `subtract` are used, do not double-count the symbolic operator

Platform output is the final authority. If platform `operatorCount > 8`, the expression is invalid even if local estimates looked safe.

### 6.3 Eight Expressions Per Round

Every round must contain exactly 8 candidates.

If any candidate is invalid before simulation because of syntax, signature, or operator-count issues, rewrite it before sending the batch so that the round still contains 8 valid candidates.

### 6.4 Named Parameters Are Mandatory

Do not guess operator usage from memory. Check the local operator library first.

Rules:

- positional required arguments must be present
- optional keyword arguments must be written as `name=value`
- naked optional literals are invalid
- if an operator definition requires keywords for clarity, use them exactly as defined

Examples:

- `winsorize(x, std=4)`
- `ts_returns(x, d, mode=1)`
- `filter(x, h="1, 2, 3, 4", t="0.5")`
- `rank_by_side(x, rate=2, scale=1)`

### 6.5 Fine-Tune Gate

Pure parameter tuning is allowed only when the current best candidate already satisfies both:

- Sharpe > 1.40
- Fitness > 0.90

If this gate is not met, the round is Stage A and zero candidates may be pure fine-tunes.

### 6.6 Negative-Signal Preservation

If a candidate has:

- Sharpe <= -1.20
- Fitness <= -0.50
- no hard disqualifying failure such as weight explosion or unit invalidity

mark it as `CAND_NEG`.

In the next round, create at least 2 flipped variants labeled `CAND_SHORTFLIP`, for example:

- `multiply(-1, expr)`
- `negate(expr)`

Do not discard strong negative signals just because they are negative.

## 7. Stage Logic

### Stage A

Use this stage when the fine-tune gate is not met.

Allowed candidate types:

1. Structural upgrades based on field behavior such as denoising, freezing, orthogonalization, turnover control, or correlation restructuring.
2. Same-dataset field combinations using at most 2 closely related fields with a clear complementarity reason.
3. Core-field plus price-volume semantics, as long as the core dataset remains frozen.

Suggested quota:

- structural upgrade: at least 3 candidates
- same-dataset combination: at least 3 candidates
- price-volume semantic combination: at least 2 candidates

Pure parameter-only edits are forbidden in Stage A.

### Stage B

Use this stage only after the fine-tune gate is met.

Recommended role split:

- `#1` to `#5`: exploit or controlled fine-tune
- `#6` to `#8`: forced explore

Explore slots must each include at least 2 theme operators from the theme set below, and the pair of themes must not repeat across the 3 explore expressions.

## 8. Theme Quota

Every 8-expression round must cover at least 4 distinct themes from A to F.

### Theme A: Conditional Trading Or Freeze

- `trade_when`
- `keep`
- `if_else`
- `nan_mask`

### Theme B: Denoising, Jump Handling, Backfill

- `days_from_last_change`
- `filter`
- `group_backfill`
- `hump`
- `hump_decay`
- `jump_decay`
- `kth_element`
- `last_diff_value`
- `ts_backfill`

### Theme C: Tail Treatment And Robust Truncation

- `clamp`
- `left_tail`
- `nan_out`
- `pasteurize`
- `purify`
- `replace`
- `right_tail`
- `tail`
- `truncate`
- `winsorize`

### Theme D: Orthogonalization And Projection

- `group_multi_regression`
- `group_vector_neut`
- `group_vector_proj`
- `multi_regression`
- `regression_neut`
- `regression_proj`
- `ts_poly_regression`
- `ts_regression`
- `ts_theilsen`
- `ts_vector_neut`
- `ts_vector_proj`
- `vector_neut`
- `vector_proj`

### Theme E: Correlation Structure

- `ts_co_kurtosis`
- `ts_co_skewness`
- `ts_corr`
- `ts_covariance`
- `ts_partial_corr`
- `ts_triple_corr`

### Theme F: Turnover, Scale, One-Side, Constraint

- `inst_pnl`
- `inst_tvr`
- `one_side`
- `rank_by_side`
- `scale`
- `scale_down`
- `ts_delta_limit`
- `ts_target_tvr_decay`
- `ts_target_tvr_delta_limit`
- `ts_target_tvr_hump`

## 9. Common-Operator Limit

These frequent operators must not dominate a round:

- `ts_sum`
- `ts_mean`
- `rank`
- `zscore`
- `winsorize`
- `ts_std_dev`
- `scale`
- `round`
- `trade_when`

Constraint:

- each operator above may appear at most 2 times across the 8 expressions

Compensation rule:

- if an expression uses 2 or more operators from the frequent set, add at least 1 extra theme operator from A to F

## 10. Required Execution Flow

### Step 0: Confirm Settings

1. Authenticate if necessary.
2. Use `get_platform_setting_options` to confirm valid combinations for `region`, `delay`, `universe`, `neutralization`, and `language`.

### Step 1: Read Baseline And Freeze Core Fields

1. Call `get_alpha_details(baseline_alpha_id)`.
2. Extract and freeze:
   - core fields or dataset family
   - current weaknesses such as noise, turnover, correlation, crowding, or instability

### Step 2: Plan The 8 Candidates Before Writing Them

For each of the 8 slots, decide:

- role: exploit or explore
- theme coverage
- whether it is structural, same-dataset combination, or PV semantic integration
- rough operator count
- common-operator usage budget

Before moving on, verify:

- there are exactly 8 candidates
- the round covers at least 4 themes from A to F
- frequent-operator caps are respected

### Step 3: Operator Preflight

For each candidate:

1. list all operators and explicit arithmetic symbols
2. look up every operator in the local operator library
3. verify existence, required arguments, optional arguments, and keyword spelling
4. reject any naked optional value or missing parameter name

If any operator is missing or malformed, rewrite the expression before validation.

### Step 4: Local Validation

For each candidate, run local expression validation before any simulation.

Required behavior:

- if invalid, repair the exact reported issue
- rerun validation until it passes
- do not degrade by deleting the core operator or replacing the expression with a trivial form just to silence the validator

### Step 5: Multi-Simulation

Run the 8 validated expressions through `create_multiSim` or the active multi-simulation tool.

If the response is truncated:

- collect all visible alpha IDs
- fetch missing metrics or expressions with `get_alpha_details`
- treat the completed per-alpha results as the only reliable round summary

### Step 6: Mandatory Post-Backtest Actions

For every candidate, in this order:

1. check for strong negative signals and mark `CAND_NEG`
2. evaluate whether the next round remains Stage A or can enter Stage B
3. reject any candidate whose platform `operatorCount > 8`
4. if all checks PASS with zero FAIL, immediately run `get_submission_check`
5. if `PROD correlation >= 0.7`, keep iterating with a decorrelation-focused next round

### Step 7: Append The Round Result File Immediately

Right after the batch simulation completes, append the 8-result round summary to the required text file.

Default naming rule when the user does not provide one:

- `<baseline_alpha_id>_optimization_results.txt`

Append mode requirement:

```python
with open(target_file, 'a', encoding='utf-8') as f:
    f.write(content)
```

The appended content should include at least:

- timestamp
- baseline alpha ID
- round index
- the 8 expressions or their short labels
- alpha IDs
- Sharpe, Fitness, Turnover, and key FAIL items
- whether submission check was triggered
- PROD correlation result when available

### Step 8: Pick The Global Best And Iterate

Select the best current candidate, including the original baseline if it still dominates, and use it as the reference for the next round.

## 11. Error Handling

### 11.1 Simulation Errors

If a simulation request fails, inspect the detailed simulation error tool first and classify the failure:

- syntax or malformed expression
- bad parameter or signature mismatch
- unit or warning issue
- NaN or data issue

### 11.2 429 Or Repeated Failures

On any 429, warning, or unexpected failure:

1. re-check every operator used in the candidate against the local operator library
2. verify argument count, keyword names, and allowed usage form
3. retry only after the operator audit is clean

Forbidden behavior:

- do not drop the core operator just to make the request pass
- do not swap in a weaker, unrelated operator as a shortcut
- do not move into fine-tuning when the stage gate still says Stage A

## 12. LLbaqEqa-Specific Prompt Pattern

When the user asks for a task such as:

- optimize JPN alpha `LLbaqEqa`
- `region=JPN`, `delay=1`
- target all PASS, `PROD correlation < 0.7`, and `IS_LADDER_SHARPE` must pass
- append every batch result to `LLbaqEqa_optimization_results.txt`

the skill must strictly follow this reference:

1. use the WorldQuant BRAIN MCP tools to inspect the baseline alpha and setting options
2. generate exactly 8 candidates per round
3. validate locally before simulation
4. simulate the batch
5. append the round results to `LLbaqEqa_optimization_results.txt` immediately
6. continue until a candidate reaches the Definition Of Done or the platform proves the current branch invalid