# Project 106Amen — R28 Scientific Revision Decision and External Audit

**Date:** 10 November 2026
**State:** R28 revised author-review manuscript candidate. It supersedes R27 for scientific *author review* after source-to-manuscript, LaTeX and PDF production checks. The archived R25-SE1 / R22 empirical baseline is immutable and never overwritten.

## Four substantive scientific-review conclusions

1. **Keep the genuine four-source result.** Three original cohorts remain locked: PROPRE.MA 3/25, EURAC 1/7, and MORE-EU 45/79 at q=5%, gap L<=3. HKUST (Library, three source-months) is a **retrospective** fourth comparison, 0/3 on the same q,L, never a blinded or source-independent probability sample. Other roofs remain secondary source screening only.

2. **Keep original metrology chain but distinguish levels.** HKUST original Zenodo 10909062 original archive SHA256 `610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec` provides source-resampled five-minute inverter powers and fifteen-minute site powers. Three fully observed Library source months / 93 days give median 0.427578% and p95 0.993528% agreement of integrated site power with the sum of integrated inverter powers. The source's published 31-Aug-2022 example independently replays: site 642.087334791 kWh vs inverter sum 641.55875 kWh; the separate site generation(kWh) field sums 651.32 kWh. This is aggregate recording consistency, not a calibration certificate of individual device gains.

3. **Add a genuinely more interpretable mathematical result** in R28: the **baseline-preserving critical relative-gain envelope**. For every source-month, minimize `max_j |eta_j-1|` over constant positive per-inverter factors and a contiguous gap <=3 days, subject to the full-month shortlist being identical to its recorded reference while the subset after omission has a different shortlist. This is a finite union of linear programs after enumerating each out-of-set exclusion challenger. The same factors must apply before and after omission. This is *not* a new theorem or measured instrument uncertainty.

4. **Explicit mathematical and scientific limits.** The value is a source-conditional break-even sensitivity, *not* a field calibration error or risk probability. Shared common-mode gains cancel exactly from the q-relative shortlist. Only independently traceable instrument calibration, operations, clock and error covariance could turn this into an engineering uncertainty guarantee; aggregated site meter agreement cannot identify individual per-inverter gain errors.

## New R28 critical-gain evidence (q=5%, gap <=3 days, percent)

| HKUST source group / month | Relaxed LP lower | Strict positive-margin feasible upper | Source state |
|---|---:|---:|---|
| Library / 2022-07 | 0.468732 | 0.468733 | Source rating identity A |
| Library / 2023-05 | 2.025260 | 2.025261 | A |
| Library / 2023-07 | 1.826765 | 1.826766 | A |
| S H Ho Sports Hall / 2022-07 | 0 | 0 | B; point-only already changed |
| S H Ho Sports Hall / 2023-05 | 0.623996 | 0.623997 | B |
| S H Ho Sports Hall / 2023-07 | 2.506853 | 2.506854 | B |
| Wong Check She / 2022-07 | 1.610532 | 1.610533 | B |
| Wong Check She / 2022-08 | 1.827069 | 1.827071 | B |
| Wong Check She / 2023-05 | no witness <=5% | no witness <=5% | B |
| Zone A2 / 2023-07 | 0.296290 | 0.296292 | B |
| Zone D / 2023-05 | no witness <=5% | no witness <=5% | C HOLD due physics/source anomalies |
| Zone D / 2023-07 | no witness <=5% | no witness <=5% | C HOLD |

All 12 source months are dependent, not pooled into one percentage; only the Library is introduced as the main paper's fourth comparison.

## Reproducibility gates

- Original source: HKUST 2024 Zenodo release, not interchangeable with later Dryad release.
- **9,360 bounded linear-program subproblems** executed for 12 source-months; 9 positive-margin source-conditional witness months. All original R26K q5 epsilon status classifications crosschecked; independent 2-inverter ratio calculation verifies 8 months without the primary LP algorithm.
- Four 3-inverter positive witnesses independently re-evaluated from original derived daily data (Library 3 + Zone A2 1), with no separate external proof of no-witness in generic three-inverter cases. Relaxed lower bounds can include equality-only boundary feasible states; the reported upper bounds have strict positive-margin observed shortlist changes.
- Original R22 q×L results and source cohort sizes unchanged. No missing-day imputation and no Qatar/QEERI data or restricted raw PROPRE.MA archive.

## Publication action

R28 revises the actual Solar Energy manuscript and supplement with (i) a formal definition and a main-text three-month critical-margin table, (ii) a supplementary 12-month source register with LP proof obligations and independent validation boundary, and (iii) a practical evidence ladder distinguishing observed deletion reliability, hypothetical measurement-factor sensitivity and measured aggregate source consistency.

**Submission remains author-controlled**: author order/affiliations/ORCIDs, CRediT contributions, funding/APC, acknowledgments, conflicts, GenAI disclosure and any journal-specific anonymization/repository release checks. Do not claim Final Submit without these. Prefer a manuscript-figures-editable Overleaf ZIP plus separate Main, Supplement, Highlights, source-linked numerical evidence and SHA256 manifest.

Project Drive: https://drive.google.com/drive/folders/1SA7r1vu1dRk_D-LFIkb5yz-s3F12A_Mo
HKUST original source repository: https://zenodo.org/records/10909062
Published descriptor: https://doi.org/10.1038/s41597-025-04397-y
R28 research branch: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/tree/r28-critical-relative-gain-margin
