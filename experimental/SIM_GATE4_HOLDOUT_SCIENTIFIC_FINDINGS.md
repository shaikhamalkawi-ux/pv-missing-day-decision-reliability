# 106Amen — SIM-GATE4 chronological one-inverter telemetry holdout
**Date:** 2026-11-17. **Manuscript baseline:** R40 unchanged. **R41:** HOLD.

Source is the original HKUST 2024 dataset, SHA-256
`610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec`,
with exact replay of all original R30 Library monthly inverter totals.

## Fixed experimental question

Can a missing single-inverter stream be bounded from **surviving inverter
streams** and **the missing inverter's observed dates outside the gap** so
that an end-of-month PV shortlist can be safely determined? The output
cannot be described as an online decision at outage onset, and surviving
peer feeds are a conditional acquisition-topology scenario.

Dataset roles: Jul 2022 training; May 2023 chronological validation; Jul
2023 final temporal holdout. Target data from the deleted interval are never
inputs to prediction, only to ex-post verification. The July model bounds
use observations from the earlier two months only, plus the July retained
days outside each counterfactual gap. The site-level stream is completely
excluded because SIM-GATE3 established its almost exact dependency on
inverter power.

For each target j in the missing period G, define p_d as the average
of the two other inverters' DC-STC-normalized observed daily yields; for
a retained set R, c_j(R)=sum_R y_j / sum_R p. The LOCAL bound is

  X_j(G) in [max(0, (1-delta_j)c_j(R)sum_G p),
                  (1+delta_j)c_j(R)sum_G p] intersect [0, U_j(G)]

where delta_j is the maximum ratio departure observed across all
1--7-day gaps of previous complete source months. LOCAL uses observed
post-gap records only when evaluating after month end. GLOBAL instead
uses the minimum and maximum previous-month daily target-to-peer ratios.
A separate physical-box comparator only uses 0 <= X_j <= U_j,
where U_j is a conditionally assumed 50 kW inverter AC capacity
multiplied by 12 daylight hours and gap length.

## Source-verified results (588 overlapping one-inverter gaps per month)

At q=5%:

| Month / stage | Method | Stable interval-list outcomes | Wrong stable outcomes | Energy interval violations | Naive wrong | Naive decision errors corrected by the predicted set (NOT certified when envelope violated) |
|---|---|---:|---:|---:|---:|---:|
| 2023-05 validation | Physical capacity | 2 | 0 | 0 | 313 | 0 |
| 2023-05 validation | Global peer ratio | 551 | 21 | 588 | 313 | 263 |
| 2023-05 validation | Local peer ratio | 588 | 0 | 1 | 313 | 313 |
| 2023-07 final holdout | Physical capacity | 42 | 0 | 0 | 311 | 0 |
| 2023-07 final holdout | Global peer ratio | 446 | 0 | 20 | 311 | 237 |
| 2023-07 final holdout | Local peer ratio | 588 | 0 | 7 | 311 | 311 |

At q=10%, July final holdout:

| Method | Stable outcomes | Wrong stable outcomes | Energy interval violations | Naive wrong | Corrected naive wrong |
|---|---:|---:|---:|---:|---:|
| Physical capacity | 3 | 0 | 0 | 425 | 0 |
| Global peer ratio | 311 | 0 | 20 | 425 | 164 |
| Local peer ratio | 433 | 0 | 7 | 425 | 270 |

Source run:
https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/44158796629

## Scientific interpretation

The local peer relationship can recover an apparently correct answer,
but its energy-bound envelope fails on some unseen gaps. At q=5% it
has zero *observed wrong decisions* in 588 July windows, and seven
*mislabeled-valid hypothetical energy intervals*. These 588 overlapping
windows are NOT 588 independent trials. Zero observed wrong decisions
does not rescue an invalid deterministic premise. The global peer method
fails particularly badly in May, where every interval violated its
training-only bound.

**No operational CERTIFY, no future coverage guarantee, no R41 admission.**
Even zero violations over these months would not turn a historical
extremum into a future guaranteed bound.

## What must happen to make this a meaningful future certification test

1. Freeze the fault mechanism **before looking at outcome**. If a single
   historian export fails but the upstream inverter is still measured,
   proof of an independently retained aggregate stream may allow its
   use; it is still not an independent meter. If the inverter measurement
   itself fails upstream, the derived site channel MUST be masked too.
2. Establish at least one genuinely separately acquired, time-aligned
   signal **available during the missing period** (external calibrated
   irradiance/independent meter, or validated independently logged
   peer streams) and establish its fault survivability. The HKUST
   paper documents a separate weather tower but does not, by itself,
   certify independent acquisition and transmission failure paths.
3. Specify a justified, auditable finite bound for missing energy,
   not merely historical min/max or a pvlib point prediction. If the
   bound is probabilistic, report marginal/time-blocked coverage and
   abstention; do not label it deterministic.
4. Freeze the source, thresholds, solver, calibration, and code, then
   evaluate genuinely later unexposed dates and independent month/roof
   groups. July 2023 is **now inspected** and may not be reused as a
   clean holdout for any post-hoc tuned envelope.
5. Report per-month/per-roof actual missing-energy containment,
   wrong issued decisions, abstentions, and **corrected naive wrong
   decisions**. Any bound miss among issued deterministic certificates
   blocks the deterministic claim.
6. Preserve the R40 core result: this candidate-specific single-device
   outage is scientifically different from the common-day, all-device
   omissions in R40. Do not pool their denominators or insert the
   provisional SIM-GATE4 outputs as published R40 main results.

## Reproduction

Python: `experimental/r40_simgate4_peer_holdout.py`.
Workflow: `.github/workflows/r40-simgate4-peer-holdout.yml`.
Run on GitHub Actions; it rehydrates the original SHA-pinned HKUST
archive from already verified research-only Actions artifact, does not
publish raw HKUST data, verifies R30 original monthly totals, and
uploads only derived summary JSON/CSV.

The next source-independent research path is a **topology-aware
identifiability experiment** with an independently available channel,
not another tuning pass on these already inspected 2023 holdouts.
