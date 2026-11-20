# 106Amen R46 — independent-meter and cumulative-counter eligibility gate (2026-11-21)

## Decision

**NO-GO for claiming operational correctness under natural missing data.** R43 remains the latest complete academic manuscript. R46 is a source-evidence research test, not a new manuscript and not a re-tuned version of R43.

### Raw-source verifications completed

PVDAQ 9068 official AC-power data (SHA-256 `16cac9d3ec61027e6f176eea276dafd1ad6d46461336edb29a3772ad34b5efc2`) contains 137,249 timestamps, two inverter total AC channels, eight module-subchannels. The original meter CSV (SHA-256 `be6662913e7ceb0888b24e6ad16c2b76eba264e2c7c0ba69d36d6e85772157b6`) has 123,872 timestamps, with 123,795 aligned. Under the fixed 10:00–14:00 / inverter sum >100 kW diagnostic, 20,414 complete source-aligned power comparisons yielded median |meter - (inverter1+inverter2)| = 1556.0 kW, median |meter + (inverter1+inverter2)| = 3260.5 kW, Pearson r = 0.33025; neither sign yields a calibrated energy balance. 132 timestamps have exactly one missing inverter total with an available meter, but the meter does not independently identify the missing inverter output. The eight internal module channels must not be treated as eight independent candidate devices.

PVDAQ 2105 contains 11 native inverter-string CSV files and one meter CSV. Both original hardware metadata releases lack populated inverter/meter mapping tables. Source files inv01 and inv02 contain a field with units kWh, but their 5-min consecutive readings decreased in 36.75% and 26.96% of transitions, respectively (114,772/312,264 and 111,237/412,555). Those fields therefore fail the interpretation of monotonically accumulating, non-reset cumulative-energy counters; no accurate lost-gap kWh can be inferred by endpoint subtraction. Source dictionaries identifying daily/interval energy would be needed before interpretation.

Honda Dryad DOI `10.5061/dryad.73n5tb363` public dataset and file metadata were accessible, but primary file downloads still returned HTTP 401/403. No Honda raw measurement was obtained, and the processed products cannot substitute as independent truth for actual gaps.

### Reproduction (public, derived-only)

- [PVDAQ9068 + Honda raw access gate](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/44817639573)
- [PVDAQ9068 sign and subchannel assessment](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/44817874174)
- [PVDAQ2105 provenance and headers](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/44818343270)
- [PVDAQ2105 actual kWh field audit](https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/44818533746)

Generated report and source evidence files: `106Amen_R46_IndependentMeter_Eligibility_Research_Report.pdf` + derived JSON. No third-party source CSV, station measurement series, or Honda raw files redistributed.

### Next gate

Only an original sensor trace that (1) independently survives the relevant inverter channel gap, (2) measures the correct electrical boundary with validated timebase and uncertainty, and (3) is linked to well-defined candidate DC-STC capacities can support correctness evaluation of a naturally incomplete shortlist. Do not claim operational safety, retune R43 against already inspected PVDAQ data, or silently recast a kWh interval reading as cumulative energy. Until admitted, retain R44 transfer failure and R45/R46 source negative findings separate from the R43 manuscript.
