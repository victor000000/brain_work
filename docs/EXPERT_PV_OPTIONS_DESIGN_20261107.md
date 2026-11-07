# Revised Expert design — November 7, 2026

## Decision and scope

Keep PV/options value inputs and the later user instruction, **atom alphas only**. Each new expression may depend on exactly one distinct numeric measurement field, including dependencies hidden behind variables. Repeated use of that field is allowed. Legitimate GROUP metadata remains partitioning only; no classifier as a numeric signal, second-field blend, risk input or analyst estimate. Validate the meaning of derived provider fields rather than treating a single identifier or `pv` prefix as sufficient compliance.

The next stage is an evidence-led discovery programme. It does not reopen the closed settings sweeps. The design deliverable does not launch simulations, change allocations or restart the service.

## Baseline and destination

Latest retained November 7 handoff: GOLD, 57 Q4 alphas, five credited pyramids; Selected CAP −1.05, all-alpha CAP −3.41, Power Pool −3.35, Osmosis null. These are retained observations, not a fresh authenticated account snapshot in this design task. The prior targets are at least 20 quarterly signals, ten pyramids and an eligible published combined score of at least 0.50. Reverify requirements and competitive eligibility from the current platform before execution. Official promotion is the completion criterion.

Under those targets, breadth is five pyramids short and the best published score is 1.55 points short. A score increase alone cannot deliver Expert. The score divergence does not establish that recent submissions caused the all-alpha decline: common dates, constituents and PnL attribution are needed.

| Proposed D1 cell | Platform Q4 count | Additional scope-valid acceptances for a three-alpha set |
|---|---:|---:|
| AMR/PV | 2 | 1, subject to seed audit |
| USA/OPTION | 2 | 1, subject to seed audit |
| ASI/PV | 2 | 2: only one existing seed passed strict scope audit |
| EUR/PV | 1 | 2, subject to seed audit |
| One additional accessible PV/options cell | No selected route yet | 3 if empty |

This route provisionally needs nine additional admissible acceptances. It assumes existing completed pyramids remain credited and their seeds pass audit. New research acceptances must be atoms; report historical seed atom compliance separately from their broader PV/options scope compliance. Do not claim the historical portfolio is atom-only. The fifth new cell is a required research decision, not optional spare capacity. If EUR offers no releasable mechanism, two new cells would be needed instead.

## What the completed work changes

- [Engineering implementation](status/DESIGN_IMPLEMENTATION_20261105.md): scope/check/ownership/quota/reconciliation/reward repairs are reported complete. Verify their active code paths, rather than scheduling the same repair programme again.
- Three controlled studies failed. AMR decorrelated volume variants remained fitness-short; pure IV exposures lacked quality; EUR weighting reduced performance. Do not repeat them with renamed tags.
- [Atom programme](status/ATOM_PROGRAMME_20261105.md): sampled volume fitness reached 0.93, reversal production correlation reached 0.9733, and tested price/spread/IV atoms failed qualification. Retain those failures and the exact configurations.
- [D0 campaign](status/D0_CLOSURE_20261107.md): retain a default no-spend decision for the tested D0 families. High headline Sharpe did not clear recent-period and robust-universe gates. Two USA examples are out of scope, and AMR 2rA7xLrJ is a two-field expression; neither can justify a new compliant atom.

The reports' claims of a universal atom ceiling or impossible D0 route exceed the finite observations. The breadth audit includes just two transferred examples in some regions. Likewise, three identical date-range results are evidence that those requests did not change the observed metrics; verify accepted/echoed settings and result identity before concluding why. These limitations do not justify rerunning the failed trials. Reopen only on a documented new mechanism, corrected implementation or changed native capability.

## Workstream 1: establish what is actually untested

Deliver a field-by-cell evidence inventory before new simulation spending. Use retained catalogues and ledgers first, then native metadata GETs where needed. Never open the live DuckDB beside its writer.

For each accessible numeric measurement record native ID, description, underlying economic quantity, category, type, units, update timing, supported delay, maturity where relevant, coverage/staleness evidence, and provenance. Record availability separately from a successfully qualified signal. Treat unavailable coverage as unknown, not zero.

Join this inventory to exact prior expressions/settings and canonical one-field mechanisms. Mark each field/cell as tested, untested, unresolved, unsupported or out of scope. Keep aliases and economically equivalent recipes together. The output must expose which provider PV/options measurements remain untested beyond basic close/returns/volume/VWAP/IV, and whether any can serve the missing tenth pyramid.

Do not infer field-level exhaustion from a few region transfers. Equally, an unused field is not a research hypothesis. No catalogue-size target or unused-field padding.

## Workstream 2: release one distinct atom study

Select at most two studies for the initial discovery cycle; release them sequentially. Each has at most three new cases, six total. This is a review budget, not a platform limit. An exact sufficiently current control may be reused. If no novel field/mechanism clears the inventory audit, release zero cases and report the missing evidence explicitly.

| Study priority | Research question | Required novelty evidence |
|---|---|---|
| Partial-cell contribution | Does a verified single measurement carry information independent of our accepted family in AMR, USA options, ASI or EUR? | An untested economic quantity or defensible temporal mechanism; explicit comparison to the retired volume/reversal/skew/flow/IV studies. |
| Missing-cell discovery | Is there an accessible D1 cell with a scope-valid one-field mechanism and credible broad/recent coverage? | Native access and measurement semantics; region-specific mechanism rather than another transfer of the failed AMR recipe. |

Choose between partial and missing-cell studies by evidence quality, not a fixed simulation quota split. Both questions must eventually be resolved for the ten-pyramid route.

For an admitted field `x`, freeze a simple one-field baseline, the proposed temporal transformation, and one component control isolating that transformation. All cases use the same field, cell and justified settings. Choose operators, direction and horizon from the source mechanism and field update frequency before seeing outcomes. These are templates for study structure, not ready-to-dispatch formulas. Do not reuse the old rank/z-score/window grids merely because they fit this structure.

Record source, exact expressions/settings, unique numeric leaves, prior-trial matches, expected direction, coverage concern and stop rule. Validate supported operators and dispatch identity. Request/receipt/terminal/qualified/accepted counts remain separate.

## Workstream 3: diagnose the binding gate

| Observation | Next decision |
|---|---|
| Missing/error/pending check | Retain candidate and owner; paced GET observation, no submission to discover a verdict. |
| Weak Sharpe or fitness | Inspect return/turnover/coverage diagnostics under the platform's actual definitions. Require a distinct explanation before further cases. A fitness value near 1.0 is not evidence that another decay will solve it. |
| Quality passes, correlation fails | Retire this exposure unless new evidence identifies independent information. Renaming or monotonic rescaling does not establish independence. |
| Recent-period or robust-universe fails | Inspect available yearly/coverage diagnostics. Failure indicates lack of required robustness, not proof of a specific causal regime story. No date-window bypass or selective removal of failing stocks. |
| All required checks pass | Review scope, atom compliance and contribution; preserve durable submission ownership, then verify actual ACTIVE/dateSubmitted and quarterly credit. |

Use native cell-specific verdicts and limits, including authoritative correlation PASS exceptions. No known-FAIL submissions. Thresholds measured in one D0 cell are not universal rules for every region/delay. A failed study closes after all cases are assessed; there is no automatic follow-up grid.

## Workstream 4: performance evidence

Keep a dated record of all four published combined measures and their observation dates. A null value stays null. Refresh on actual platform changes or useful review points; do not treat the historical 4–6-week documentation as a guaranteed update date.

From scope-audited accepted alphas, record actual OS availability, family, region, horizon and costs. The November 5 inventory reported no OS yet for the 57 Q4 alphas. Verify availability before attribution. If aligned native PnL exists, establish daily/cumulative semantics and overlapping dates, then compare a fixed baseline and the incremental contribution of each family. Make allocation choices using training evidence; repeatedly inspected historical TEST is reused validation. New accrued OS remains independent evidence.

If PnL is unavailable, say portfolio attribution is unavailable. Do not average alpha Sharpes into a combined score, claim dilution improves negative CAP, or remove historical alphas to manufacture compliance. Inspect current Power Pool/Osmosis access only as a conditional route; no allocation change is part of this design.

## Delivery order and release criteria

1. **Evidence pack:** refreshed requirements/account totals, reconciled scope/atom inventory, protected unresolved-owner list, exact trial coverage and a candidate tenth cell. Preserve the nine historical pending owners in the handoff; audit scopes/counts separately rather than interpreting an unrelated zero-uncertain dispatch audit as their resolution.
2. **First decision:** publish one frozen three-case study if a novel question passes every release condition. Otherwise publish the specific field/access/semantics gap and spend nothing on repeats.
3. **Study review:** assess all cases and native checks; release the second study only if it answers a distinct remaining question.
4. **Breadth:** verify six, then eight, nine and ten native pyramids, alongside strict scope and atom counts. If no credible tenth-cell route exists, label the Expert plan incomplete rather than declaring eight or nine sufficient.
5. **Performance:** verify published best score above zero, then the freshly confirmed Expert floor; verify actual promotion separately.

The concrete next action is the field/mechanism coverage inventory, not another volume, reversal or D0 sweep. This task writes a new design only; execution must preserve the existing writer, current authorization state, native quotas and uncertain owners. No promotion date or success probability is supported by the available evidence.
