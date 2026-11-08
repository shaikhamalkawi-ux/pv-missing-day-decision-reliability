# 106Amen R26K — Baseline-preserved calibration and missing-day audit

**Scientific development gate, 8 November 2026. Do not alter R25-SE1 / frozen R22 results.**

## Why this gate was required

In R26J, the existence of a source-conditioned shortlist change used one fixed relative-calibration vector for full and deleted-day data. However, the resulting full-month shortlist might itself differ from the recorded-data reference, so an observed gap effect could be confused with a changed reference decision.

R26K adds a separate, stronger condition: for each source month, the **same** inverter-specific gain vector must (i) leave the recorded full-month shortlist intact, with a positive numerical membership/exclusion margin and then (ii) produce a different shortlist after deletion of a contiguous block of up to three observed days. There is no imputation or retuning of q or L.

Source: HKUST original [Zenodo 10909062](https://zenodo.org/records/10909062), publisher ZIP SHA-256 `610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec`. The corresponding article is Lin et al., *Scientific Data* 12, 63 (2025), [doi:10.1038/s41597-025-04397-y](https://doi.org/10.1038/s41597-025-04397-y), which reports ±2.5% accuracy for direct electrical readings and ±5% for calculated generation power/energy. **That report does NOT establish independent actual instrument errors or their correlation.** The present factors are hypothetical and constant for an entire month by study design.

## Frozen decision and sensitivity design

- Decision rule: `S(q;D,eta)={j: eta_j Y_j(D) >= (1-q) max_k eta_k Y_k(D)}`; `q=5%`.
- Source observed yield: five-minute site inverter AC `totalActivePower(W)` integrated as summed equal-cadence samples and divided by its source-traced module DC-STC denominator.
- Calendar source-month: all 144 native five-minute slots from 06:00 to 17:55 for each day and all co-roof device files, finite measured power, at least ten retained days after deleting any contiguous block of 1, 2 or 3 whole days.
- Hypothetical per-inverter constant factors `eta_j in [1-eps,1+eps]`, with epsilon = 0%, 0.25%, 0.5%, 1%, 2%, 3%, 5%.
- R26K baseline preservation: the full-month shortlist under the **same** eta equals the recorded-data reference shortlist. Near-boundary solver-only equality without positive numerical membership/exclusion margins is not certified.
- If eta_j is identical for every inverter (perfect common-mode gain), the factor cancels exactly; recorded-value missing-day decision fragility is unchanged. Hence the study audits *relative* gain sensitivity, not common-mode error.

## Source-conditional outcome at q=5%, L<=3

Table entries count source-months with an **existence** witness. These are NOT probability or calibration-error frequencies, and the five groups share one campus.

| Same-roof group | 0% | 0.25% | 0.5% | 1% | 2% | 3% | 5% | Source grade |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Library | 0/3 | 0/3 | 1/3 | 1/3 | 2/3 | 3/3 | 3/3 | A: source rating identity |
| S H Ho Sports Hall | 1/3 | 1/3 | 1/3 | 2/3 | 2/3 | 3/3 | 3/3 | B: AC/DC station basis unresolved |
| Wong Check She Research Centre | 0/3 | 0/3 | 0/3 | 0/3 | 2/3 | 2/3 | 2/3 | B |
| Zone A2 | 0/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | B |
| Zone D | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | C: electrical-source HOLD |

At the 5% development envelope, all nine positive R26J *unrestricted-reference* cases also have a witness preserving the original full-month baseline, with the identical gain vector on the omitted-day data. This closes the ambiguity that a changed R26J baseline alone manufactured the gap effect. It does **not** establish that any physical inverter is miscalibrated.

For the strongest source identity (Library), one of three months already admits a source-month-baseline-preserving omission under a 0.5% hypothetical *relative* factor bound, whereas all three admit such a witness at a 3% or larger bound. Conversely, all three Library months were stable under deletion using the recorded energy values (epsilon=0) at the same q, L<=3.

## Reproducibility and numerical claim boundary

Primary original-source-derivative run [42513250336](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42513250336): 84 month×epsilon source-cell classifications (12×7), 35 group×epsilon aggregate cells, 12/12 match with the R26I point-only q=5%, L<=3 result, nondecreasing existence in epsilon, and consistency with the previously verified R26J eps5 envelope.

Independent analytic run [42513338503](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42513338503): 56/56 source-month×epsilon cells from two-inverter groups independently recomputed by a **no-SciPy, interval-ratio partition** across full/gap thresholds; 15 positive three-inverter witness scenarios recomputed directly under source-relative factors. Three-inverter negative LP infeasibility results have not received an independent symbolic or vertex-enumeration proof. Do not claim otherwise.

An initial independent cross-check found a numerical boundary disagreement at epsilon 1%. The primary LP implementation was tightened to require positive reference membership margins and the independent checker to reject boundary-only states, then the **whole grid** was rerun, not selectively patched. The source QA must retain that documented refinement. No source data, q, L, or observed-day records were modified.

## Publication decision and next valid evidence

**DO NOT promote R26K into the R25-SE1 journal manuscript as a calibrated measurement-uncertainty result or fourth externally validated source.** Its contribution is an evidence-gated diagnostic insight: deletion-based stability of a set-valued PV decision and identifiability of that set under allowed device-relative measurement factors are distinct questions. Any general claim requires actual calibration/covariance information or an independently justified device-error model. External solar-irradiance series at the site do not supply this metrological covariance.

This is an applied PV decision audit, not a new general case-removal theorem, ranking theorem, or probability estimate. Do not pool co-roof source months. Qatar/QEERI data are excluded. The frozen R25 reproducibility branch and author-review PDFs are unchanged.
