# 106Amen R44 — independent-site transfer and real-missingness evidence gate

**Decision (2026-11-21): NO-GO for operational external validation. The R43 manuscript is not modified.** R44 is a research/QA gate, not a new journal manuscript.

## Frozen R43 rule on PVDAQ 2107

- Original source: NREL PVDAQ/OEDI system 2107, 24 ABB inverter channels, original source files from 2024/2025 fixed by SHA-256.
- R43 threshold **-0.001077879123675074**, q=5%, exactly 3 common-day deletions; no external threshold fitting.
- **2024 all-positive cohort:** 6 months, 169 windows, 14 changed shortlists (all from Oct 2024), **TP=0, FP=0, FN=14, TN=155**, AUC=0.9976958525.
- **2024 zero-inclusive source-policy sensitivity:** 8 months, 227 windows, still 14 changed and 0 review alerts, AUC=0.9983232730.
- Independent original-CSV replay (month-minus-gap vs direct retained sums): **PASS** for both confusion matrices and AUC.
- 2025 strict 10:00–14:00 common-support: only February/July qualify, 55 windows and no changed lists; AUC undefined and this is not evidence of success.
- Other normalization choices changed outcomes and are scientifically distinct estimands; do not conflate them.

## Real original-source gaps

2025 electrical data have **9,899** absent 10:00–14:00 inverter device-slots and **170** device-days with no complete midday reading, including 49-, 47- and 40-day consecutive device-run gaps. These are telemetry absences, NOT independently proven equipment failures or observed zero generation.

The 2025 *revenue-grade* meter file contains 35,036 quarter-hour readings on all 365 dates. When the 15-minute meter and 5-minute inverter channels are aligned to the source-declared left timing convention, the complete-channel meter-minus-inverter sum has median absolute **14.068 kW** and p95 absolute **139.065 kW** over 3,568 matched intervals. There are 2,037 source intervals with exactly one missing inverter channel and a meter reading, but the meter residual is not a justified physical missing-inverter energy bound.

## Strong claim boundaries

1. Name-suffix pairing of the 24 module groups and 24 inverter channels is a *conditional inference*: provider metadata do not explicitly join module group to inverter ID, and panel counts differ by group. Technical wiring metadata required before treating nominal-DC-normalized results as engineering evidence.
2. PVDAQ metadata's 'mono-Si' descriptor conflicts with the California Energy Commission's HiS-M310TI polycrystalline listing; no technology ranking may use this source label without reconciliation.
3. 2024/2025 electrical releases overlap in 2024 dates; year-specific filtering used, never merged naively.
4. These are dependent artificial common-day deletions plus descriptive real missing-data inventory, **not prospective correctness validation** or independence evidence.
5. Do **not** refit R43 cutoff on this inspected PVDAQ source and then call it a clean external replication.

## Source-locked reproducibility

- Source inventory: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/44811312579
- Frozen transfer: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/44812253923
- Independent replay: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/44812534612
- Actual field gap inventory: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/44812816406
- Revenue meter timebase: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/44813059913
- Full derived-only R44 report/archive: https://drive.google.com/drive/folders/1gzd9Y_NEKuIpcJRutlgZnejN1FVoiRaQ

R44 report 5 pages; all derived JSON, evidence ledger, scientific gate, and integrity manifest are in the Drive ZIP. No third-party original electrical or meter rows were redistributed.

**Next numbering:** R45 only after an admissible new scientific correction, source-owner wiring/calibration evidence or author-controlled production request; R43 remains last full journal article pending these gates.
