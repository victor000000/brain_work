# Submission Workflow

## API Flow
1. After local selection, scope review and the native preview/correlation path, `POST /alphas/{id}/submit` sends a new request
   - 201: request received (NOT necessarily accepted)
   - 403: rejected, body contains FULL check results
2. After 201, reconcile the existing request with GET requests only:
   - `GET /alphas/{id}`: a native submission date confirms submission. Reports
     of a currently accepted alpha also verify `status == ACTIVE`.
   - If its date is still missing, `GET /alphas/{id}/submit` observes the
     asynchronous submission decision. Honor positive Retry-After within the
     remaining polling window; HTTP 200 alone does not confirm acceptance.
   - HTTP 403 with genuine native FAIL checks records a rejection. A quota-only
     failure defers the candidate without retiring it.
   - HTTP 404, transport failures, malformed responses and ERROR/PENDING checks
     leave request ownership intact. They do not authorize another POST.
3. `GET /alphas/{id}/check` — PREVIEW only (async may stay PENDING). Do not use
   it to restart an already-owned submission request.

The normal owner implements this in `runner/verify_submit.py` and
`runner/submit_progress.py`. It probes an expired progress resource once per
verification round, continues checking the alpha date, and never downgrades a
previously verified request from a stale progress response.

## Check Result Types
- PASS: meets threshold
- FAIL: below threshold
- WARNING: informational
- PENDING: async check not resolved
- ERROR: check itself failed to run

## Must-Pass Checks
| Check | Rule |
|---|---|
| LOW_SHARPE | sharpe >= threshold (varies by region) |
| LOW_FITNESS | fitness >= 1.0 |
| LOW/HIGH_TURNOVER | 0.01 <= turnover <= 0.7 |
| CONCENTRATED_WEIGHT | weight not too concentrated |
| LOW_SUB_UNIVERSE_SHARPE | works in sub-universes |
| SELF_CORRELATION | native verdict; commonly displayed limit 0.7 (async) |
| PROD_CORRELATION | native verdict; commonly displayed limit 0.7 (async) |
| IS_LADDER_SHARPE | stable across time periods |
| LOW_COVERAGE | >= 5% |
| POWER_POOL_CORRELATION | <= 0.5 (async) |

## Key Insight
POST /submit initiates async checks that GET /check may leave PENDING. The
submission-progress resource can return the final 403 even while alpha metadata
still says UNSUBMITTED with no submission date. A native FAIL is authoritative;
an unavailable observer is not a rejection.

Preserve explicit native correlation PASS even above a displayed scalar limit.
For example, XgRn2YRl passed native production correlation at 0.7331 and became
ACTIVE on 2026-10-19. The former local scalar override falsely rejected it.

The saved official consultant rules also describe a higher-Sharpe alternative
for correlated submissions. Current native comparison records illustrate why
checking only the scalar is insufficient: A1QPX0al has self-correlation 0.8734
to XgRn2YRl, but its Sharpe 3.28 exceeds 1.1 times 2.87 (3.157), and its
native preview says PASS. Conversely, 2rjLgje8 has correlation 0.8156 to
xA1eX91J, with Sharpe 2.48 versus 3.57, and its native preview says FAIL.
These are eligibility observations, not acceptance or OS-performance claims.
Keep the native verdict authoritative; do not replace it with a locally
reconstructed exception. Evidence:
brain_logs/native_correlation_conditional_rule_reconciliation_20261019.json.

Simulation-time warnings are preliminary. Several saved below-floor results
had no initial FAIL rows but fresh submission previews returned actual Sharpe,
concentration or production-correlation failures. A simulation WARNING must not
be treated as submission approval or used alone to relax eligibility.

Confirm recordset date coverage before calling a PnL series out of sample.
An alpha being ACTIVE or appearing in the OS alpha list does not establish
that its downloaded series includes the OS period. Keep historical test
metrics, submitted OS metrics and the consultant's combined scores separate.
The dated native coverage audit is saved in
`brain_logs/accepted_alpha_recordset_date_audit_20261019.json`.

## Local Eligibility Filter

Single source of truth: `runner/submit/eligibility.py`. Submission tools use the shared selector. `tools/reconcile_submissions.py` selects transient eligible rows and uses GET observations plus local DB updates; it is not a new-submission CLI.

| Constant          | Value | Mirrors                            |
|-------------------|-------|------------------------------------|
| `MIN_SHARPE`      | 1.58  | LOW_SHARPE (EUR/d1; conservative)  |
| `MIN_FITNESS`     | 1.0   | LOW_FITNESS                        |
| `TURNOVER_MIN`    | 0.01  | LOW_TURNOVER                       |
| `TURNOVER_MAX`    | 0.7   | HIGH_TURNOVER                      |
| `MIN_TEST_SHARPE` | 0     | Positive historical test-period Sharpe; not submitted OS performance |

The actual shared selector uses the per-(region, delay) floor map in
`runner/submit/eligibility.py`, with 1.58 as the fallback. It also applies the
region-specific turnover ceiling (IND: 0.4). Keep those rules shared with the
reporting parser; do not infer a new threshold from an incomplete simulation
check set.

Not enforced locally:
- `IS_LADDER_SHARPE` — requires native checks; it is not derived from the local
  summary metrics.
- `LOW_COVERAGE` — requires field metadata/native checks rather than the local
  `alpha_results` summary columns.

## Published 1.0.1 scope guard and limitations

The new-request path in runner/submit/flow.py checks readable regular code with core/scope.py before PATCH/POST. An existing submission owner instead follows reconciliation. Name-based semantic checks are not complete metadata or atom-role validation; unavailable/malformed expression payloads currently cause guard abstention. Preview handling in this published tree is not identical to later private working-tree experiments. Read [Research](docs/RESEARCH.md) for policy versus implementation and never treat missing verdicts as permission.
