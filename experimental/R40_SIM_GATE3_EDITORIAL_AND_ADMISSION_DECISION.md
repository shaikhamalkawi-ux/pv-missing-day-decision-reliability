# R40 SIM-GATE3 / SIM-GATE3B - original-source correction decision (16 Nov 2026)

**Source gate:** PASS for corrected timebase, numerical source lineage and exact legacy
replay. **Operational CERTIFY:** HOLD. **R40 manuscript and its inverter-only
decisions:** unchanged; **R41:** not opened. This development note is not a
new journal paper or a revision of the locked R40 scientific result baseline.

Original HKUST source: Zenodo 10909062, byte-pinned SHA-256
`610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec`.
Admitted source-audit cohorts were taken unchanged from the R26I register.
See independent completed source runs
[Library SIM-GATE3](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/43820405621)
and [all-roof SIM-GATE3B](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/43821197373).
The all-roof run's derived-only artifact contains exact machine-readable output.
No source archive is republished.

## Confirmed error in old R40 source comparison

The legacy R26L method and R40 Supplement S4a computed site energy from
**all 96 fifteen-minute samples over 24 hours** while computing inverter
energy from **144 five-minute samples over 06:00-18:00**. The historical
Table S5 medians and p95s reproduce exactly, but their apparent channel
discrepancy includes site energy outside the inverter time window. For a
matched 06:00-18:00 support, the source agreement becomes near-exact.

| Roof | Days | Old median (%) | Same-window median (%) | Same-window p95 (%) | Maximum native site-feed minus 3x5-min mean (W) |
|---|---:|---:|---:|---:|---:|
| Library | 93 | 0.427577888 | 0.000000381 | 0.000001116 | 0.010000 |
| S H Ho Sports Hall | 93 | 0.358252127 | 0.000005207 | 0.000016893 | 0.046667 |
| Wong Check She Research Centre | 93 | 0.310829576 | 0.000000455 | 0.000001120 | 0.003333 |
| Zone A2 | 31 | 0.753139652 | 0.000000350 | 0.000000721 | 0.006667 |
| Zone D | 62 | 0.347835736 | 0.000004307 | 0.000013575 | 0.043333 |

The 15-minute site stream equals, to tiny source-rounding residuals,
the forward average of **three consecutive 5-minute summed-inverter
power samples** in all five cohorts (17,856/17,856 daylight timestamps
have absolute residual <=0.1 W). This is numerical lineage, not evidence
of a separate meter or a guarantee that this stream would survive an
upstream data loss.

In the separately audited 2022-08-31 Library example, site 24-hour
energy was 642.087334791 kWh, site 06-18 energy 641.5587514575 kWh,
and summed inverter 06-18 energy 641.55875 kWh. The old difference
0.528584791 kWh is 0.5285833335 kWh of out-of-window site energy plus
0.0000014575 kWh same-window residual.

## Consequences for missing-data counterfactuals

* **Upstream source failure:** deleting an inverter's originating
  telemetry but leaving its site aggregate available can leak masked
  information. The no-site conditional 50-kW-cap route gave just 44/1176
  stable q=5% certificates in the 2023 one-inverter holdout and fixed none
  of the 624 erroneous naive decisions.
* **Downstream export failure:** allowing a pre-computed site aggregate
  to survive is a *different* scenario that must be justified externally.
  Its assumed +/-2% envelope yielded 1176/1176 provisional stable 2023
  holdout decisions and 624 corrected naive errors, but the survival
  pathway and error envelope were not independently certified.
* **Full upstream loss with weather/pvlib:** out-of-period model bounds
  failed, and there is no deterministic certificate.
* The SE50K published 50,000-VA maximum output rating can support a
  *conditional* physical-capacity analysis if actual variants and operating
  conditions are verified. It cannot establish gain uncertainty or a
  universal field-output certificate.

## Exact editorial correction requested

1. Rewrite Section 3.5 to identify the historical unmatched hours,
   distinguish provider-derived aggregate from independent measurement,
   and use the corrected Library medians.
2. Replace Figure 5 (not only its caption): use a time-support diagnostic,
   with no claim of second independent meter confirmation.
3. Rewrite Supplement S4a; replace Table S5 with old vs matched-support
   medians/p95s for all five roofs, preserving their source-admission states.
4. Add the upstream-vs-downstream failure-mode caveat to the Discussion,
   retaining the site-feed tests only as conditionally illustrative.
5. Rebuild a *separately versioned editorial review copy* of the actual
   R40 source and rerun scientific invariant tests. Do not alter any R40
   inverter decision count, monthly cohort, paper model, or conclusion.

## Executable exact-source tests

- `experimental/r40_simgate3_timebase.py` (Library, published example);
  workflow `.github/workflows/r40-simgate3-timebase.yml`.
- `experimental/r40_simgate3_all_roofs.py` (all five R26I source-audit cohorts);
  workflow `.github/workflows/r40-simgate3-all-roofs.yml`.
- Previous negative results:
  [site-aggregate test](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/43771461481);
  [pvlib out-of-period test](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/43770641811).

**Interpretation boundary:** The source numerical dependency is supported by
data. The precise physical instrument architecture, the actual point of a field
outage, independent calibration, and future uncertainty coverage are not
established. Five source checks are not five independent decision cohorts.
