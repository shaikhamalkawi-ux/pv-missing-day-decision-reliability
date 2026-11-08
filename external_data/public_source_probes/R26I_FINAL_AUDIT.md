# 106Amen R26I — HKUST independent-source and weather audit

**Research-only status: source conditional / DO NOT integrate into R25-SE1.** Original R22 scientific outcomes and the public r25-public-release are unchanged. No Qatar or QEERI data were used.

## Authoritative external sources
- Original HKUST data: https://zenodo.org/records/10909062 ; archive SHA-256 `610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec`.
- Article: Lin et al., *Scientific Data* (2025), DOI `10.1038/s41597-025-04397-y`. The publisher synchronized raw collection to regular time labels, left missing entries as NA with no filling, and reported approx. ±5% accuracy for derived generation power.
- Original inverter data have 144 observed five-minute slots per source-clock day (06:00–17:55), not 288 readings for a full 24 hours. Shared on-campus weather station irradiance is sampled at 1 minute. Weather irradiance is **not per-rooftop plane-of-array** irradiation.

## Fixed admission logic
Five co-located multi-inverter roof groups were found in the original source; twelve group-months passed a strict calendar-month observed-power/clock gate. We mapped all inverter-to-PV-module relationships via original Brick RDF, including multiple module types, and computed each device denominator as the sum of module-count × module-STC-W. Station rating was audited *separately*, never silently substituted for DC module STC. The station-to-DC-STC ratio can reflect AC/DC rating bases and is not intrinsically an error.

| Roof group | Complete power months | Station rating / summed module DC STC | Power samples >120% device module STC | Source quality tier |
|---|---:|---:|---:|---|
| Library | 3 | 1.0000 | 0 | A — exact source rating identity |
| S H Ho Sports Hall | 3 | 0.8547 | 0 | B — rating basis unresolved |
| Wong Check She Research Centre | 3 | 0.8379 | 0 | B — rating basis unresolved |
| Zone A2 | 1 | 0.9941 | 0 | B — slight station/source rating mismatch |
| Zone D | 2 | 0.7272 | 1,589 | C — source/operation review hold |

The 120% threshold is an alert for review, not a validated fault definition or physical tolerance. Zone D's metadata also require additional identity review; no device-failure claim is made.

## Source-conditional development calculations
For each group, the exact existing R22 no-imputation shortlist is used with q=(0,2.5%,5%,7.5%,10%) and L=1..7 days, at least 10 retained observed days. Outcome uses the sum of observed inverter AC-power samples / each device's original module DC-STC denominator. This is a declared site-inverter observation, not intrinsic technology efficiency.

| Group | q=5%, L<=3, source-only |
|---|---|
| Library | 0/3 |
| S H Ho Sports Hall | 1/3 |
| Wong Check She Research Centre | 0/3 |
| Zone A2 | 0/1 |
| Zone D | 0/2 (HOLD) |

Exactly 420 underlying group-month-q-L decisions and 175 group-q-L cells were independently recomputed with full byte-level alignment, fixed cohorts, witness checks, and nondecreasing L. PASS.

## Shared weather availability sensitivity
Source meteorological irradiance matched at each inverter native five-minute stamp:
- July 2022 4464/4464 finite unique; August 2022 4464/4464;
- May 2023 4464/4464;
- July 2023 **4463/4464**: one source clock timestamp absent on **30 July 2023**; no values filled.

A **100% weather-complete auxiliary admission policy** removes July 2023 as a climate-supported month; a **95% finite-day criterion** retains it. Neither policy was present in R22; both are sensitivity checks, not retuned decisions.

| Group | no weather gate (q5,L<=3) | weather 100% | weather >=95% |
|---|---:|---:|---:|
| Library | 0/3 | 0/2 | 0/3 |
| S H Ho Sports Hall | 1/3 | 1/2 | 1/3 |
| Wong Check She Research Centre | 0/3 | 0/3 | 0/3 |
| Zone A2 | 0/1 | 0/0 | 0/1 |
| Zone D (HOLD) | 0/2 | 0/1 | 0/2 |

**0/0 means no admitted months, not a measured stable decision.** Fractions are within-roof descriptions, not independent binomial trials or general PV outage probabilities.

## Admission decision and next valid work
**HOLD manuscript revision.** A new scientifically certified fourth cohort requires independently justified station/inverter denominator semantics, mapping of operational states, and metrological uncertainty treatment. The paper's q=5% is a shortlist inclusion rule, not the ±5% electrical measurement uncertainty nor a confidence interval.

R26I is valuable as a documented negative/conditional portability gate and illustrates that criteria for admitting complete *weather* and *electricity* records are distinct, without implying either is universally required. Publish no new causal climate effect, technology-superiority claim, or pooled risk. No raw donor data are in the research code repository. No Qatar or QEERI data were consulted.

## Reproducibility
- Exact isolated research branch: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/tree/r26i-hkust-capacity-sensitivity
- Independent source + arithmetic CI run: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42503693629
- Physical admission tier QA: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42504128089
- Shared-site irradiance read: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42504382277
- Integrated weather admission sensitivity: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42504603108

All source-bound analyses were kept on the separate development branch. The original manuscript and R25 fixed publication release were not updated.
