# Publication and data boundaries

- This public directory contains **publication-level summary data** (CSV), not source telemetry.
- The 3 original source cohorts remain supported by the original repository's R25 public code and results.
- The fourth HKUST source was retrospectively added; further checks and exact-q calculations are described in the Supplement and preserved in a separate controlled verification archive, not wholly copied here.
- The standalone Python script runs only an audit on *already complete and qualified* user-supplied source-month daily normalized yields. Its tests use synthetic fixtures; passing does not revalidate raw field data.
- The PVDAQ transfer study is conditional on an unverified inverter-module pairing and gave zero flags for 14 known retrospectively changed shortlists under the frozen threshold.
- No restricted PROPRE.MA raw records or raw EURAC, MORE-EU, HKUST, or PVDAQ files were copied into this directory.
- Do not interpret missing source rows as zero power. Do not use the included software as a deployed diagnostic, alarm, fault detector, procurement decision, or guarantee of natural-outage correctness.
- Publication declarations, full authorship, source redistribution permissions, and the release DOI remain author-stage items. No final journal acceptance is claimed.
