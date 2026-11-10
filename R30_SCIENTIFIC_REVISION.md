# Project 106Amen — R30 Solar Energy Expert Review and Same-Missing-Rate Evidence

**Status:** Scientific author-review candidate; NOT submitted or author-approved.
**Target:** Solar Energy (Elsevier), 10 November 2026.

## Scientific delta vs R29

- From original source-derived HKUST Library July 2023 31 complete inverter days, q=10%, examine each of 25 exactly seven-day contiguous deletions. Three positions change the shortlist (5–11, 7–13, 8–14 July) while 22 preserve it. Every position omits the exact same 7/31 fraction. At q=10%, all three inverters start in the full-month set and inverter 3 drops in each of the three changing windows. This is a deterministic counterfactual, NOT an observed field-outage frequency, an independent-trials probability, or measured calibration.
- Add a main Results discussion and Supplement Table S8 plus machine-readable 25-window CSV and independent two-route arithmetic validator.
- Explicitly identify the originally complete admitted source months and artificially deleted day windows in Abstract, Methods, Supplement and Conclusion; no imputation.
- Reorder the existing 15 references by FIRST APPEARANCE, without adding/altering DOI values; fix the abstract percent notation for every decision margin.
- Preserve R22 locked counts at q=5%, L<=3: PROPRE.MA 3/25, EURAC 1/7, MORE-EU 45/79, retrospective HKUST Library 0/3.
- Preserve R28 critical hypothetical gain margins 0.468733%, 2.025261%, 1.826766% and R29 independent graph verification (4,680 alternatives; max absolute lower-bound difference below 4e-13 relative to LP); do NOT imply a measured sensor error law.

## Scientific interpretation and limits

Only the library is an admitted HKUST fourth-source case; other roofs remain secondary or on HOLD. Three months on one roof are dependent and retrospective. Source decision objects across the four cohorts are nonexchangeable and should not be pooled or interpreted as comparative technology reliability. Integrated AC inverter output per DC-STC device rating is a source-window specific-yield proxy, not module efficiency or irradiance-normalized performance ratio. Close aggregate station/inverter recording agreement is not individual device calibration. No Qatar/QEERI or restricted donor raw records are used or distributed.

## Reproducibility

Run `python code/verify_publication_results.py`, `python code/rebuild_released_surface.py`, `python code/r28_verify_science.py`, `python code/r28_replay_bundled.py`, `python code/r29_independent_logratio_graph.py`, `python code/r30_equal_rate_gap_position_audit.py`, and `python code/r30_publication_assertions.py`. Required source-derived R26I/R26K records are downloaded by the archived GitHub CI workflow and included in the resulting reproducibility ZIP.

## Author gates

Author names and order, affiliations, ORCID, CRediT, funding/APC, acknowledgements, conflicts, AI-use declaration, anonymization route, source/public-release permissions and final journal portal requirements require approval. Not submission ready until completed.
