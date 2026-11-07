# PV Missing-Day Decision Reliability

Public reproducibility materials for the manuscript:

**When Missing Days Change a Photovoltaic Comparison Decision: A No-Imputation Reliability Surface Across Three Field Datasets**

## What this repository contains

This repository supports a PV-domain decision-reliability study that asks whether a declared candidate shortlist remains unchanged when whole observed days are unavailable. Missing energy is **not imputed** in the primary analysis.

The locked analysis uses three materially different sources:

- **PROPRE.MA (Morocco):** restricted donor archive; only derived, non-raw results are released here.
- **EURAC (Bolzano, Italy):** public dataset on Zenodo, DOI `10.5281/zenodo.18316996`.
- **MORE-EU:** public `OpenData` repository; the analysis pins `Array Power.csv` Git blob `5611277efdd581bb839ec380239846a43ebe0ba7`.

The study does **not** claim a new generic case-removal robustness principle, intrinsic PV-technology superiority, a procurement error probability, or a causal climate effect.

## Repository structure

```text
paper/       manuscript/Supplement LaTeX; CI-generated review PDFs
code/        analysis and verification scripts
results/     locked derived result tables and result certificates
figures/     CI-generated central q x gap-length reliability surfaces
metadata/    source and literature registers
```

## Review PDFs

The reproducibility workflow builds and commits:

- `paper/106Amen_R25_JournalNeutral_Main.pdf`
- `paper/106Amen_R25_Supplementary_Material.pdf`
- `paper/106Amen_R25_Main_plus_Supplement.pdf`

If these PDFs are not yet present immediately after repository initialization, check the `Reproducibility and PDF build` GitHub Actions run; the generated files are committed after the first successful build.

## Locked primary design

- shortlist margin: `q in {0, 2.5%, 5%, 7.5%, 10%}`
- contiguous whole-day gap length: `L = 1,...,7`
- at least 10 retained days
- no missing-day energy imputation
- datasets are analyzed separately and are not pooled into a single failure probability

At `q=5%` and gaps no longer than three days, the locked fragile-month counts are:

- PROPRE.MA: `3/25`
- EURAC: `1/7`
- MORE-EU: `45/79`

These are descriptive source-specific counts, not independent-trial probabilities.

## Quick public reproduction

### 1. Create an environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

### 2. Rebuild the publication figures from locked released tables

```bash
python code/plot_decision_reliability_surface.py \
  --surface results/R22_DECISION_RELIABILITY_SURFACE.csv \
  --out figures/rebuilt
```

### 3. Verify the locked publication counts

```bash
python code/verify_publication_results.py
```

### 4. Re-run the public EURAC branch

Download the official EURAC archive from Zenodo and run:

```bash
bash code/r19_eurac/reproduce_all_r19.sh /path/to/EURAC.rar /path/to/output
```

The scripts verify the expected source checksum before analysis.

### 5. Re-run the public MORE-EU branch

Obtain `Solar Park Data -INACCESS/Array Power.csv` from the official MORE-EU repository at the pinned Git blob and run:

```bash
python code/r20_more_eu/reproduce_r20_more_eu.py \
  "/path/to/Array Power.csv" \
  /path/to/output
```

The R22 MORE-EU script additionally checks the pinned Git blob SHA.

## PROPRE.MA rights boundary

Raw PROPRE.MA donor files are intentionally **not redistributed**. The public repository contains only derived publication-level tables/figures and analysis code that does not embed donor raw bytes. Full raw-source replay of the PROPRE.MA branch therefore requires authorized access to the restricted donor archive.

## Data sources

- EURAC Research, *EURAC photovoltaic data*, Zenodo v1: https://doi.org/10.5281/zenodo.18316996
- MORE-EU/OpenData: https://github.com/MORE-EU/OpenData
- PROPRE.MA background publication: https://doi.org/10.1016/j.esd.2019.09.002

## Reproducibility status

The manuscript integrates locked R22 results. Upstream project QA reported exact cross-stage reproduction of the `q=5%`, `L<=3` counts and clean-source compilation of the manuscript and Supplementary Material. See `results/R22_RESULT_CERTIFICATE.json` and `paper/`.

## License and citation

- Analysis code in `code/`: MIT License (see `LICENSE_CODE_MIT.txt`).
- Third-party datasets retain their original licenses and are **not** redistributed here.
- Manuscript, figures, and derived result tables are provided for scholarly review and reproducibility; copyright remains with the authors unless a later release states otherwise.

Author metadata is intentionally not invented here. See `CITATION_TEMPLATE.md`; a machine-readable `CITATION.cff` should be added only after the final author list and ORCIDs are approved.

## Continuous verification

GitHub Actions reruns the locked result checks, rebuilds the three q x gap-length surfaces, compiles the journal-neutral manuscript and Supplementary Material, and commits the generated review PDFs back to the repository.
