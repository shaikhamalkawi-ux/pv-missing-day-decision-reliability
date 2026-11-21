# Author-review reproducibility snapshot — 22 November 2026

**Manuscript:** *When Missing Monitoring Days Change Photovoltaic Screening Shortlists: A Four-Source Retrospective Audit*.

This is the versioned R55-EP2 **repository-availability integration** of the locked R55-EP1 research and editorial manuscript. The numerical science, original equations, 37 bibliographic identities, and 11 author-approved figure assets are unchanged. The PDF and TeX contain editorial link/status changes only. This is an author-review artifact, **not a published journal article or validated field-outage alarm**.

## Files

- `paper/main.pdf`, `paper/supplement.pdf`: complete current author-review PDFs; `main.tex`, `supplement.tex`: corresponding sources.
- `figures/*.pdf`: exactly 11 locked source graphics (seven Main, four Supplement).
- `code/pv_shortlist_retrospective_audit.py`: runnable pure-Python **complete historical-month shortlist deletion audit** (only the set-comparison operation).
- `code/test_pv_shortlist_retrospective_audit.py`: synthetic software tests, not validation on PV field data.
- `data/source_access_register.csv`: official original-data providers and redistribution boundary.
- `data/locked_published_summary.csv`: printed publication-level aggregate results, not original telemetry.
- `FILE_SHA256.json`: hashes of the snapshot content; run `python verify_snapshot.py` for byte checks.
- `RELEASE_SCOPE.md`: public-data and scientific claim boundaries.

## Minimal demo

```bash
python code/test_pv_shortlist_retrospective_audit.py
python code/pv_shortlist_retrospective_audit.py --help
python verify_snapshot.py
```

To use the script, provide a **complete, already qualified** daily CSV with `month,date,candidate,normalized_yield`; `code/qualified_daily_template.csv` shows the header. Script usage and stop conditions are also in Supplementary Section S9. It does not reproduce the original site admission, full source analyses, exact-q search or PVDAQ holdout, and cannot assess correctness for an actually incomplete month.

## Data access and interpretation

Original raw data are **not redistributed**. PROPRE.MA donor records are restricted; EURAC, MORE-EU, HKUST and PVDAQ have separate provider holdings and applicable terms. See `data/source_access_register.csv`, `DATA_AVAILABILITY.md` at repository root and manuscript Supplementary Section S7. The original three-source public reproduction remains under older root paths and the source-pinned subsequent analyses under historical branches. This snapshot contains publication-level summaries and a limited stand-alone implementation, not a complete independently replayable four-source raw-data archive.

**Repository root:** https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability
**Snapshot:** https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/tree/main/release/2026-11-22-r55-ep2

## Publication status

Author-stage declarations, author metadata, repository licensing and any permanent DOI remain subject to final author review. The GitHub commit URL identifies this source snapshot; no Zenodo DOI has been assigned.
