# R26L — Actual paired-measurement evidence for Project 106Amen

**Development-only audit — 9 November 2026. Locked journal-facing R25-SE1 remains unchanged. Qatar/QEERI is excluded.**

## Real problem and evidence users

R26J/R26K demonstrated *possible* q=5% shortlist changes under hypothetical, fixed, inverter-specific measurement gain boxes. Those tests do not establish actual gain magnitudes, cross-inverter error dependence, or field calibration. A manuscript reviewer needs to distinguish (1) source integrity, (2) aggregate measurement-channel agreement, (3) device-relative calibration, and (4) decision sensitivity under missing observed days. None of these is interchangeable.

The original public HKUST source is [Zenodo 10909062](https://zenodo.org/records/10909062), initial 2024 release, publisher original ZIP SHA256 `610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec`. Related published Data Descriptor: [Lin et al. (2025), *Scientific Data* 12, 63, doi:10.1038/s41597-025-04397-y](https://doi.org/10.1038/s41597-025-04397-y).

## Two distinct observed recording channels actually available

- **Site channel:** `Site level dataset/<roof>.csv`, native 15-minute `Time`, `generation(kWh)`, and `power(W)`. There are up to 96 clock records per day.
- **Inverter channels:** `Inverter level dataset/<roof>_Inverter_j.csv`, native 5-minute `Time`, `totalActivePower(W)`; the published monitoring interval is 06:00–17:55 with 144 five-minute clock records per day.
- **Source lineage:** the publisher applied timestamp resampling but explicitly did **not** fill missing data or remove outliers. These are the *original published data* rather than untouched device-native raw telemetry.
- **Metric:** comparison uses each complete day's `sum(site power(W))*0.25/1000` vs `sum over all roof inverters [sum(inverter totalActivePower(W))/12/1000]`, in kWh. No interpolation; the two native source sampling rates are retained.
- **Admission:** source whole-calendar-month cohorts inherited exactly from R26I. All devices within a cohort day must have 144 unique finite five-minute values, while the site-level daily record must have 96 unique finite 15-minute values for both power and generation. No partial day filled; 372/372 source-cohort days pass the matching source-clock gate.

## Exact published reference reproduction

For the Library site on **31 August 2022** (separate article figure-reproduction check, not one of R26I's three complete source months):

| Component | Published, kWh | Recomputed from original source, kWh |
|---|---:|---:|
| Inverter 1 | 175.77 | 175.77325 |
| Inverter 2 | 251.88 | 251.88075 |
| Inverter 3 | 213.90 | 213.90475 |
| Site channel, integrated `power(W)` | 642.09 | 642.087334791 |
| Absolute site-minus-inverter energy | 0.529 (reported) | 0.528584791 |
| Relative difference, min-denominator convention | ~0.08% | 0.08239% |

**Important source variable distinction:** summing the site channel's separate `generation(kWh)` column yields **651.32 kWh** for that same day. This is **not** the same observable as integrating site `power(W)`, nor does the discrepancy establish that either field is erroneous. Interval-energy interpretation, logger transformations and sampling statistics require distinct provenance. If the paper compares power-integrated energy, do not silently replace it with `generation(kWh)`.

## Observed site vs inverter source consistency in R26I complete months

The following statistics describe `100*abs(E_site_power_integral - E_sum_inverter_power_integral)/min(E_site,E_sum_inverter)`. p50 and p95 were recomputed independently from source-derived daily records.

| Same-roof comparison group | Matched days | Median relative disagreement | p95 |
|---|---:|---:|---:|
| Library | 93 | 0.42758% | 0.99353% |
| S H Ho Sports Hall | 93 | 0.35825% | 0.82787% |
| Wong Check She Research Centre | 93 | 0.31083% | 0.78540% |
| Zone A2 | 31 | 0.75314% | 1.14705% |
| Zone D (electrical/source HOLD) | 62 | 0.34784% | 0.90492% |

**Do not pool percentages into a site-independent estimate.** They share one university campus, different inverter geometries, instrumentation lineages, and months. The Zone D cross-channel sum agrees even though source inverter power values exceeding 1.2 times the source-derived module-DC-STC were previously observed: aggregate agreement is **not** a per-device anomaly clearance.

## What the new evidence establishes and what it cannot

1. **PASS — reproducibility**: matched two distinct logged power channel types, reconstructed the published 31-Aug-2022 Fig. 6 example to two-decimal rounding, and independently rechecked 372 day-level comparisons, 5 group counts, 20 reported group percentiles. No imputed source values.
2. **PASS — descriptive consistency**: site-power-integral versus sum-of-inverter-power-integrals are close on the admitted source days, with observed native-clock integration differences documented.
3. **HOLD — independent calibrated reference**: the site meter and inverter outputs may share vendor software, signal pathways, timestamp processing, and systematic biases. No instrument-specific independent calibration certificate, traceable reference uncertainty, or covariance record has been admitted.
4. **HOLD — per-inverter gain inference**: a low residual in the aggregate `E_site - sum_j(E_inverter_j)` is one scalar constraint on many possible inverter-specific biases, and other terms (loss, sampling alignment, meter offsets) are not identified. With nonzero losses or shared errors, neither the ±5% publisher specification nor the observed median aggregate discrepancy identifies the actual relative gain factors of each inverter.
5. **HOLD — physical uncertainty admission into main paper**: R26J/R26K provide mathematically possible fixed gain scenarios, not observed error rates or confidence limits. The two axes—deletion stability and metrological identification—must remain separately reported.

## Strongest practical route to genuinely calibrated evidence

A lab or original data custodian would need to supply, for the **exact** roof inverter and site channels: instrument models and unique identifiers, calibration certificates and dates, metrological traceability/measurement ranges, field configuration/topology, sample/aggregation/clock conventions, independent cross-meter status, logger firmware and processing, AC connection/loss boundary, drift/maintenance records, and any cross-channel measurement-error covariance. Mere vendor datasheet accuracy or comparing on-site weather with PV output does not replace those inputs.

If those records are unavailable, report the cross-channel **consistency** test and data-conditioned critical relative-gain breakpoints as *analytical sensitivity diagnostics*, not calibrated engineering uncertainty. The paper can remain sound and relevant without pretending to have new calibration measurements.

## Research reproducibility

Source byte audit: HKUST Zenodo 10909062 SHA above, archive CRC PASS. Frozen R26I source month cohorts were reproduced exactly; every 5-minute inverter sum replays its previously admitted daily source sum. Output includes a day-level matched table, source-level column comparison, group descriptive statistics, published-example exact reproduction JSON and independent QA certificate.

Development branch: [r26l-station-inverter-crossmeter-audit](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/tree/r26l-station-inverter-crossmeter-audit). Main R25 project GitHub release stays unchanged. Qatar/QEERI never used.

**Conclusion:** R26L is empirical source-channel corroboration that strengthens the reliability of the *data provenance*; it is not device-level calibration or independent external validation of a generalized q×L robustness conclusion. Keep the R25-SE1 journal-facing manuscript unchanged unless a source admissibility review or genuine editorial request justifies a bounded supplement addition.
