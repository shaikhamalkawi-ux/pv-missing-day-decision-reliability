# R26J — Missing-day stability versus relative-calibration sensitivity

**Research-only independent source audit, 8 November 2026.** No scientific or submission change to R25-SE1 / locked R22. Qatar/QEERI excluded.

Source: [HKUST original public PV monitoring archive, Zenodo 10909062](https://zenodo.org/records/10909062), publisher ZIP SHA256 `610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec`. Technical source: Lin et al., [Scientific Data 12, 63 (2025)](https://doi.org/10.1038/s41597-025-04397-y), which reports approximately ±5% measurement accuracy for *calculated* generation power and energy. The assumption below is an exploratory stress, **not a statistical confidence interval or observed calibration error**.

## Conditional calibration stress (NOT field metrology)

For each inverter j in one source month, multiply its daily observed DC-STC-normalized AC yield by a *single fixed* factor eta_j between 0.95 and 1.05, including the full reference and the omission of any contiguous whole-day block. Factors may differ across inverters in this deliberate worst-case envelope. Reevaluate the existing frozen R22 shortlist with q=5% and L<=3 days. No data are filled or retuned.

| Same-roof group | Recorded-data shortlist changed | Possible under *some* fixed per-device ±5% calibration factors | Source grade |
|---|---:|---:|---|
| Library | 0/3 | 3/3 | A — source rating equality |
| S H Ho Sports Hall | 1/3 | 3/3 | B — site and device rating bases unresolved |
| Wong Check She Research Centre | 0/3 | 2/3 | B |
| Zone A2 | 0/1 | 1/1 | B |
| Zone D | 0/2 | 0/2 | C — unusual power values, HOLD |

Fractions are source- and device-conditioned descriptive counts. **Never pool them to claim actual outage probability.**

**Notable result:** all three Library months were recorded-value stable through L<=7 days at q=5%, but each admits a one-day witness of changed shortlist under *some* common-through-time, inverter-specific factors in the bounded ±5% stress. This is possible mathematical sensitivity, not a measured miscalibration. The same common gain applied to all inverters cancels in the relative shortlist, leaving the original R22 decision exactly unchanged; therefore calibration dependence matters.

## Independent numerical checks

- Source-gated daily panel outputs/ratings and original HKUST data SHA are frozen from R26I.
- Exact candidate inclusion/disqualification LP under the **same** calibration vector on full and gap-retained source data, with positive exclusion slack and explicit witness check.
- Eight two-inverter source-months verified by an independent analytic calibration-ratio partition, with no LP library.
- Four three-inverter source-months independently verified using explicit witness factors and direct shortlist recomputation.
- **12/12 independent checks PASS**, previous point-only R26I q=5% source-month outcomes reproduced exactly.
- Full portable derived-data/reproducibility archive and report: [R26J private Project 106Amen Drive](https://drive.google.com/drive/folders/1PBpREJizkGdW1R0ffQOufOossT_XzhNI).
- Primary research run: [GitHub Actions 42508843473](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42508843473).
- Independent QA run: [GitHub Actions 42509160909](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42509160909).
- Portable package QA: [GitHub Actions 42509457651](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42509457651), ZIP CRC and internal SHA256 PASS.

## Scientific boundary

This is a **separate audit dimension**, not a newly calibrated physical uncertainty analysis, not a new mathematical robustness theorem, and not a validated fourth cohort for the journal paper. The accuracy figure in the dataset descriptor does not establish independence or time invariance of calibration across actual inverters. Do not convert q=5% into metrological confidence. R25-SE1 remains the journal-facing version pending source-specific final evidence; branch `r26j-hkust-calibration-gap-audit` is development-only.
