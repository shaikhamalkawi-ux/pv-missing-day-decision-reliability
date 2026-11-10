# 106Amen R29 — Independent log-ratio graph certificate and production closure

**Status: Author-review scientific candidate; not submitted to Solar Energy.**

R29 does not change any R22/R25 locked empirical result, R28 LP result or measured-source figure. It adds an independent, solver-free verification of the R28 baseline-preserving hypothetical inverter-gain radius:

- For each fixed challenger and deletion, log-positive inverter gain comparisons are difference constraints on a directed graph.
- A negative cycle rules out the closed comparison scenario; otherwise, the shortest-path minimum log-gain spread is Delta=max(0,-min d(a,b)).
- The minimum symmetric gain-envelope radius for that *closed scenario* is tanh(Delta/2). This remains a relaxed lower envelope where the shortlist requires strict exclusions; independent strictly feasible gain vectors witness the upper bounds.
- 4,680 independent graph alternatives were checked for 12 source-months, matching the original 9,360 strict/relaxed LP calls. All 9 positive-witness thresholds agree with the LP lower bounds to maximum absolute difference 3.56e-13 (gain-fraction units). The 3 other secondary/held-source cases have closed graph thresholds beyond the tested <=5% gain envelope.

The retrospective HKUST Library's three numerical thresholds are unchanged: July 2022 0.468732% lower / 0.468733% feasible upper; May 2023 2.025260% / 2.025261%; July 2023 1.826765% / 1.826766%. Original q=5%, L<=3 counts remain PROPRE.MA 3/25, EURAC 1/7, MORE-EU 45/79, HKUST Library 0/3. No Qatar/QEERI data or pooled failure probability.

**Production corrections:** The supplement now imports the caption package so Tables S1-S7 render without erroneous "Table N: *" prefixes or caption text entering the table body. The main table's "HKUST Library" label remains on one line and duplicate run-in heading punctuation was removed.

**PV engineering clarification:** The HKUST Library specific-yield statistic integrates inverter AC output over the recorded source-daylight window and divides by nameplate DC-STC module power; this is not DC module efficiency, irradiance-normalized performance ratio, or device calibration. Official IEC 61724-1:2021 was added as a monitoring-convention citation (15/15 cited references). Aggregate site-meter agreement cannot identify individual inverter gain errors.

The full author-review reproducibility package should include the pure-Python graph checker, source-derived R26I/R26K inputs, R28 LP strict witness certificates, R22 locked results, main and supplementary PDFs, and editable LaTeX. No restricted PROPRE.MA donor raw records are redistributed.

**Submission gate:** Author order, affiliations/ORCID, CRediT, funding/APC, conflicts, acknowledgements, AI-use declaration, repository release/license, and final Solar Energy portal instructions still require author approval. R29 is not a journal submission.
