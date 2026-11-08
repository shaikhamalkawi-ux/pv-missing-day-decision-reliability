#!/usr/bin/env python3
"""R26I cross-source weather eligibility sensitivity only, not a new PV result.

Use pre-existing, source-gated HKUST outcome file without changing any
candidate yield or q/L. Compare complete 100% weather support and independent
95% per-day meteorological support (sensitivity, NOT an R22 rule).
"""
import csv,collections,json,hashlib
from pathlib import Path
E=Path("evidence");W=Path("weather");O=Path("R26I_Integrated_SourceAudit");O.mkdir(exist_ok=True)
def rows(p):
    return list(csv.DictReader(p.open(encoding="utf8",newline="")))
tier=rows(E/"SOURCE_BASED_TIER_REGISTER.csv")
decision=rows(E/"GROUP_MONTH_DECISION_GRID.csv")
weather=rows(W/"WEATHER_DAY_FIVE_MIN_ALIGNMENT.csv")
summaries=rows(W/"WEATHER_MONTH_SUPPORT.csv")
assert len(tier)==5 and len(decision)==420
assert sum(int(r["expected_5min_slots"]) for r in weather)==4*31*144
monthly=collections.defaultdict(list)
for r in weather:
    monthly[r["month"]].append(r)
strict={m for m,rs in monthly.items() if all(int(r["full_weather_support"])==1 for r in rs)}
support95={m for m,rs in monthly.items() if all(int(r["finite_unique_slots"])/144>=0.95 and int(r["duplicates"])==0 for r in rs)}
assert support95==set(monthly)
incomplete=[r for r in weather if int(r["full_weather_support"])!=1]
assert len(incomplete)==1,("Unexpected weather quality condition",incomplete)
assert incomplete[0]["month"]=="2023-07",incomplete
permonth=collections.defaultdict(list)
for r in decision:
    if float(r["q"])==.05 and int(r["L"])==3:
        permonth[r["group"]].append(r)
summary=[]
for t in tier:
    g=t["group"]
    subset=permonth[g]
    assert subset
    for policy,allowed in (("no_weather_requirement",set(monthly)),("weather_100pct_each_day",strict),("weather_95pct_each_day",support95)):
        rs=[r for r in subset if r["month"] in allowed]
        summary.append(dict(group=g,tier=t["quality_tier"],policy=policy,
                            admitted_months=len(rs),fragile_months_q5_L3=sum(int(r["changed"]) for r in rs),
                            months=";".join(sorted(r["month"] for r in rs))))
with (O/"WEATHER_POLICY_CONDITIONAL_Q5.csv").open("w",newline="",encoding="utf8") as f:
    wr=csv.DictWriter(f,fieldnames=list(summary[0]));wr.writeheader();wr.writerows(summary)
status={
 "source":"HKUST Zenodo 10909062 original archive, no replacement/imputation",
 "q":0.05,"L":3,"sample_support":"06:00–17:55 PV 5-minute source clock",
 "weather_coverage":summaries,"strict_weather_full_months":sorted(strict),
 "weather_per_day_95pct_months":sorted(support95),
 "days_with_nonfull_weather":incomplete,
 "per_roof_q5_sensitivity":summary,
 "strict_weather_criterion_role":"secondary admission-only sensitivity; R22 never required shared weather",
 "independent_roofs":"No pooling: same HKUST campus, dependent site histories",
 "no_qatar":True,"r25_unchanged":True,"status":"PASS_SOURCE_SCREEN_DEVELOPMENT_ONLY"}
(O/"R26I_FINAL_CONDITIONAL_SCIENCE_GATE.json").write_text(json.dumps(status,indent=2))
report=[
"# R26I source-only conclusion — HKUST independent datasets",
"",
"Status: DEVELOPMENT/HOLD; main manuscript R25-SE1 and original R22 scientific results unchanged.",
"",
"## Independent original evidence",
"2024 Zenodo original HKUST 60-rooftop source SHA256 610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec, source-weather checked at original 5-minute 06:00..17:55 PV-clock times.",
"Original sensor data in HKUST publisher archive include site-level irradiance (1-minute raw source), which must not be represented as a calibrated per-rooftop plane-of-array irradiance measurement.",
"Publication source: https://www.nature.com/articles/s41597-025-04397-y ; dataset: https://zenodo.org/records/10909062 .",
"",
"## Unexpected weather missingness at a complete power-source month",
]
for r in incomplete:
    report.append("Observed incomplete shared-irradiance source day "+r["date"]+": "+r["finite_unique_slots"]+"/144 finite unique matched 5-minute values, "+r["present_slots"]+"/144 time labels present; no reconstruction.")
report +=[
"At a 100%-complete shared-weather month requirement, July 2023 is excluded from the four candidate source months, whereas a 95%-finite daily threshold preserves all four. Neither rule changes previously calculated inverter power sums or the R22 q-L mathematical formula. The 95% weather threshold here is sensitivity-only, not transferred EURAC certification.",
"",
"## Frozen q5, at most 3-day gap: effect of auxiliary weather completeness",
"",
"| Same-roof group | Source-only | Weather 100% day | Weather >=95% day |",
"|---|---:|---:|---:|"
]
for t in tier:
    g=t["group"]
    row=lambda name:next(r for r in summary if r["group"]==g and r["policy"]==name)
    fmt=lambda r:f'{r["fragile_months_q5_L3"]}/{r["admitted_months"]}'
    report.append("| "+g+" | "+fmt(row("no_weather_requirement"))+" | "+fmt(row("weather_100pct_each_day"))+" | "+fmt(row("weather_95pct_each_day"))+" |")
report +=[
"",
"## Scientific claim boundary",
"Tier A source match is exact only for Library; other groups' station rated output may have AC/DC measurement-basis differences. Zone D remains HOLD due anomalous readings and station/device lineage. All months are dependent observations from HKUST roofs.",
"Power-source result replication: 420/420 exact month-q-L checks and 175/175 aggregate cells passed independent verification; group classification is based on pre-outcome source quality, not maximization of a result.",
"No new true outage probability, technology superiority, causal weather inference or metrological confidence certificate is established.",
"The manuscript R25-SE1 remains untouched, and there are no Qatar or QEERI records in this project branch."
]
(O/"R26I_DECISION_AND_WEATHER_REVIEW.md").write_text("\n".join(report)+"\n",encoding="utf8")
hashes=[]
for f in sorted(O.iterdir()):
    if f.is_file() and f.name!="SHA256SUMS.txt":
        hashes.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n")
(O/"SHA256SUMS.txt").write_text("".join(hashes))
print("R26I_WEATHER_AND_Q5_GATE",json.dumps(status),flush=True)
print("R26I_SOURCE_POLICY_SENSITIVITY_PASS",flush=True)
