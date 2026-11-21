# Data and code availability — updated 22 November 2026

**Current author-review snapshot:** https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/tree/main/release/2026-11-22-r55-ep2

The versioned snapshot contains both manuscripts (PDF and TeX), 11 unchanged approved figure PDF files, a limited public complete-month comparison script and synthetic tests, publication-level numerical summaries and an explicit source-access register. It is **not** an independently replayable full four-source raw-data archive. The historical public R25 code in `code/` and numerical tables in `results/` remain available as the original three-source reproducibility record.

## Original monitored sources

| Source | Data-holder link | Access / permission | Coverage in current paper |
| --- | --- | --- | --- |
| PROPRE.MA | https://doi.org/10.1016/j.esd.2019.09.002 | Donor-restricted raw counter data; not republished | 25 source-qualified months |
| EURAC | https://doi.org/10.5281/zenodo.18316996 | Obtain official source archive and observe its licence; not mirrored | 7 observed-system months |
| MORE-EU | https://github.com/MORE-EU/OpenData | Original CC BY-NC source; do not mirror raw data | 79 complete-array months; original `Array Power.csv` Git blob `5611277efdd581bb839ec380239846a43ebe0ba7` |
| HKUST Library | https://zenodo.org/records/10909062 | Original publisher's source and terms; not mirrored | 3 retrospective single-roof months; archive SHA-256 `610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec` |
| NREL PVDAQ 2107 | https://doi.org/10.25984/1846021 | Original provider OEDI; not mirrored | Conditional independent-site review cutoff test, not a fifth main source |

## Result and script boundaries

The publication-level source-matched counts and derived indicators are copied from the locked manuscript into the current snapshot's `data/locked_published_summary.csv`; they do not expose source raw rows. The included standalone Python script implements only the admitted retrospective shortlist operation on complete and pre-qualified daily inputs, with synthetic tests. It does **not** reproduce source admission, the full four-source numerical pipeline, exact-q certified interval calculations, gain diagnostics, holdout score calibration or field-outage correctness. The controlled extended source-linked evidence archive remains outside the public snapshot.

Historic source-pinned branch evidence in this repository includes `r42-moreeu-candidate-count-rateonly-audit`, `r43-moreeu-retained-margin-timeholdout` and `r44-pvdaq2107-external-source-eligibility`. See Supplementary Sections S4i--S4l for source identity, calculations and limits. The NREL module-to-inverter pairing is not independently validated, so the transfer finding remains conditional.

## Rights and publication status

No restricted or third-party raw monitoring records are redistributed as part of the synchronization. Public source links do not imply unrestricted redistribution rights. The author-review manuscript and supplementary files are not a certified journal version, and the current GitHub release is not assigned a persistent DOI. Original author-stage disclosures remain subject to confirmation. The code's underlying MIT terms do not override the third-party data rights.
