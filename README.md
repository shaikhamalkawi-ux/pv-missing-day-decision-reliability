# PV Missing-Day Decision Reliability

This is the public repository supporting the author-review manuscript **When Missing Monitoring Days Change Photovoltaic Screening Shortlists: A Four-Source Retrospective Audit** (22 November 2026). It studies whether a declared near-best-yield comparison shortlist changes when common consecutive days are removed from qualified complete monitoring months. The tested retrospective shortlist is **not** a fault detector, maintenance queue, operational alarm or guarantee about actual missing-data periods.

## Current manuscript, figures and data-access guide

**[Current author-review snapshot: R55-EP2](release/2026-11-22-r55-ep2/README_RELEASE.md)**

- [Main manuscript (PDF)](release/2026-11-22-r55-ep2/paper/main.pdf)
- [Supplementary Material (PDF)](release/2026-11-22-r55-ep2/paper/supplement.pdf)
- [Main followed by Supplementary Material (PDF)](release/2026-11-22-r55-ep2/paper/main_then_supplement.pdf)
- [LaTeX source and approved vector figures](release/2026-11-22-r55-ep2/paper/main.tex)
- [Published aggregate results only](release/2026-11-22-r55-ep2/data/locked_published_summary.csv)
- [Original-data access register](release/2026-11-22-r55-ep2/data/source_access_register.csv)
- [Runnable complete-month shortlist script and synthetic tests](release/2026-11-22-r55-ep2/code/)
- [Integrity verifier and manifest](release/2026-11-22-r55-ep2/verify_snapshot.py)

The latest manuscript uses four non-pooled sources: PROPRE.MA, EURAC, MORE-EU and a retrospective HKUST Library subset. The separate conditional NREL PVDAQ test evaluates a frozen review cutoff on another site. The manuscript and its supplement explain the scope and limitations; source-specific records are not exchangeable.

## Scientific snapshots and historical branches

The older root `paper/`, `code/`, `results/` and `figures/` retain the **original three-source R25 public reproduction**, not the current four-source author-review paper. They remain in place for scientific provenance. Additional public source-pinned investigations were published on historical branches, including:

- [`r42-moreeu-candidate-count-rateonly-audit`](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/tree/r42-moreeu-candidate-count-rateonly-audit)
- [`r43-moreeu-retained-margin-timeholdout`](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/tree/r43-moreeu-retained-margin-timeholdout)
- [`r44-pvdaq2107-external-source-eligibility`](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/tree/r44-pvdaq2107-external-source-eligibility)

These source-specific branches are *not* identical to a single end-to-end raw-data replay of the current four-source paper. The old R25 root workflow continues to reproduce its own locked results.

## Public reproduction and data restrictions

Run the limited standalone reader on already source-qualified, complete daily normalized-yield data:

```bash
python release/2026-11-22-r55-ep2/code/test_pv_shortlist_retrospective_audit.py
python release/2026-11-22-r55-ep2/verify_snapshot.py
```

The original raw source files are **not redistributed** in this repository: restricted PROPRE.MA donor records require authorization; the public source archives for EURAC, MORE-EU, HKUST and NREL PVDAQ must be obtained directly from their respective providers and used under the providers' terms. See [DATA_AVAILABILITY.md](DATA_AVAILABILITY.md) and Supplementary Section S7. Original derived summary counts are not probabilities of field outages.

## Publication and citation status

This is a reproducibility and author-review repository, not an accepted journal publication. Bibliographic author metadata, permissions, licences for any wider redistribution and DOI have not been finalized. See [citation guidance](CITATION_TEMPLATE.md) before citing. Code licences are project-specific, with existing original analysis code under MIT; third-party source data retain their original terms.
