#!/usr/bin/env python3
"""SIM-GATE3: HKUST Library source-timebase and channel-lineage correction gate.

Compare the older asymmetric 24-h site / 12-h inverter computation against a
same-time-support comparison. Source checksum pinned; no raw data republished.
Development audit only; no revision to R40 and no R41 admission.
"""
from __future__ import annotations
import calendar
import csv
import datetime as dt
import hashlib
import io
import json
import math
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path

SRC = Path("source/dataset_original_Zenodo10909062.zip")
OUT = Path("R40_SIM_GATE3_Timebase")
OUT.mkdir(parents=True, exist_ok=True)
SHA = "610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
BASE = "Dataset/Time series dataset/PV generation dataset/PV stations with panel level optimizer/"
SITE = BASE + "Site level dataset/Library.csv"
INV = [BASE + f"Inverter level dataset/Library_Inverter_{j}.csv" for j in range(1, 4)]
MONTHS = ("2022-07", "2023-05", "2023-07")
REFDAY = "2022-08-31"
W5 = {f"{h:02d}:{m:02d}:00" for h in range(6, 18) for m in range(0, 60, 5)}
W15 = {f"{h:02d}:{m:02d}:00" for h in range(6, 18) for m in (0, 15, 30, 45)}
ALL15 = {f"{h:02d}:{m:02d}:00" for h in range(24) for m in (0, 15, 30, 45)}
assert len(W5) == 144 and len(W15) == 48 and len(ALL15) == 96

target = set()
for month in MONTHS:
    year, mo = map(int, month.split("-"))
    target.update(f"{month}-{d:02d}" for d in range(1, calendar.monthrange(year, mo)[1] + 1))
target.add(REFDAY)
sha = hashlib.sha256()
with SRC.open("rb") as f:
    for chunk in iter(lambda: f.read(8 << 20), b""):
        sha.update(chunk)
assert sha.hexdigest() == SHA, "Original dataset SHA-256 mismatch"

def load(z, path, field):
    days = defaultdict(dict)
    with z.open(path) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
        assert "Time" in reader.fieldnames and field in reader.fieldnames
        for row in reader:
            ts = row["Time"]
            date, clock = ts[:10], ts[11:]
            if date not in target:
                continue
            assert clock not in days[date], ("duplicate", path, ts)
            val = float(row[field])
            assert math.isfinite(val), ("nonfinite", path, ts)
            days[date][clock] = val
    return days

with zipfile.ZipFile(SRC) as z:
    assert z.testzip() is None
    site = load(z, SITE, "power(W)")
    inv = [load(z, path, "totalActivePower(W)") for path in INV]

def relative_percent(a, b):
    return 100.0 * abs(a-b) / min(a,b) if min(a,b) > 0 else float("nan")
def percentile(vals, p):
    s = sorted(vals)
    pos = (len(s)-1)*p
    lo = int(pos)
    return s[lo] + (pos-lo)*(s[min(lo+1, len(s)-1)]-s[lo])
def concise(v):
    return round(v, 12)

records = []
clock_diff = defaultdict(list)
for date in sorted(target):
    sr = site[date]
    assert set(sr) == ALL15, ("incomplete_site", date, len(sr), sorted(set(sr)^ALL15)[:5])
    iv = [x[date] for x in inv]
    for j, d in enumerate(iv):
        assert W5.issubset(d), ("missing_device_daylight", date, j, len(d))
    full_site_kwh = sum(sr.values())/4000.0
    aligned_site_kwh = sum(sr[t] for t in W15)/4000.0
    inv_day_kwh = sum(sum(channel[t] for t in W5) for channel in iv)/12000.0
    outside_kwh = full_site_kwh - aligned_site_kwh
    pre6_kwh = sum(sr[t] for t in ALL15 if int(t[:2])<6)/4000.0
    post18_kwh = sum(sr[t] for t in ALL15 if int(t[:2])>=18)/4000.0
    assert abs(pre6_kwh+post18_kwh-outside_kwh)<1e-8
    for time in sorted(W15):
        hour, minute, _ = map(int,time.split(":"))
        tt = dt.datetime.strptime(date+" "+time, "%Y-%m-%d %H:%M:%S")
        clocks = [(tt+dt.timedelta(minutes=5*k)).strftime("%H:%M:%S") for k in range(3)]
        assert all(t in W5 for t in clocks)
        upstream = sum(sum(channel[t] for channel in iv) for t in clocks)/3.0
        clock_diff[date[:7]].append(sr[time]-upstream)
    records.append({
       "date": date,
       "cohort": int(date != REFDAY),
       "legacy_full24_site_kwh": full_site_kwh,
       "native_day12_inverters_kwh": inv_day_kwh,
       "matched_day12_site_kwh": aligned_site_kwh,
       "site_outside_06_18_kwh": outside_kwh,
       "site_pre06_kwh": pre6_kwh,
       "site_post18_kwh": post18_kwh,
       "legacy_absolute_diff_kwh": abs(full_site_kwh-inv_day_kwh),
       "aligned_absolute_diff_kwh": abs(aligned_site_kwh-inv_day_kwh),
       "legacy_absolute_diff_pct": relative_percent(full_site_kwh, inv_day_kwh),
       "aligned_absolute_diff_pct": relative_percent(aligned_site_kwh, inv_day_kwh),
       "signed_legacy_minus_outside_kwh": (full_site_kwh-inv_day_kwh)-outside_kwh,
    })

cohort = [r for r in records if r["cohort"]]
assert len(cohort) == 93
legacy = [r["legacy_absolute_diff_pct"] for r in cohort]
aligned = [r["aligned_absolute_diff_pct"] for r in cohort]
# Independently reproduces the frozen R26L, R27, R40 reported percentiles.
assert abs(statistics.median(legacy)-0.42757788815049586)<1e-6, ("prior_p50", statistics.median(legacy))
assert abs(percentile(legacy,.95)-0.9935278571786557)<1e-6, ("prior_p95", percentile(legacy,.95))
assert max(abs(r["signed_legacy_minus_outside_kwh"]-(
    r["matched_day12_site_kwh"]-r["native_day12_inverters_kwh"])) for r in records) < 1e-8
# Independent exact-forward aggregation audit, not same-instant samples.
assert all(max(abs(v) for v in diffs) <= 0.011 for diffs in clock_diff.values())
reference = next(r for r in records if r["date"] == REFDAY)
assert abs(reference["legacy_full24_site_kwh"]-642.087334791)<1e-6
assert abs(reference["native_day12_inverters_kwh"]-641.55875)<1e-6
assert abs(reference["aligned_absolute_diff_kwh"])<0.0001

summary = {
    "gate":"R40_SIM_GATE3_SOURCE_TIMEBASE",
    "original_sha256":SHA,
    "status":"DEVELOPMENT_ONLY; R40 UNCHANGED; R41 HOLD",
    "days":len(cohort),
    "reference_date":REFDAY,
    "legacy_integral_support":"SITE 00:00-24:00 vs INVERTERS 06:00-18:00",
    "matched_integral_support":"SITE 06:00-18:00 vs INVERTERS 06:00-18:00",
    "legacy_difference_pct":{"p50":statistics.median(legacy),"p95":percentile(legacy,.95),"max":max(legacy)},
    "aligned_difference_pct":{"p50":statistics.median(aligned),"p95":percentile(aligned,.95),"max":max(aligned)},
    "exact_support_decomposition":{
        "max_abs_unexplained_legacy_difference_kwh":
            max(abs(r["signed_legacy_minus_outside_kwh"]) for r in records),
        "max_abs_aligned_energy_difference_kwh":
            max(r["aligned_absolute_diff_kwh"] for r in records),
        "full24_minus_day12_is_outside_energy_plus_aligned_residual":True,
    },
    "per_month":{
       m:{"days":sum(r["date"].startswith(m) for r in cohort),
          "n_native_site_15min":len(clock_diff[m]),
          "forward_site_reconstruction_mae_W":statistics.mean(abs(x) for x in clock_diff[m]),
          "forward_site_reconstruction_maxabs_W":max(abs(x) for x in clock_diff[m]),
          "legacy_p50_pct":statistics.median(r["legacy_absolute_diff_pct"] for r in cohort if r["date"].startswith(m)),
          "aligned_p50_pct":statistics.median(r["aligned_absolute_diff_pct"] for r in cohort if r["date"].startswith(m)),
          "outside_power_kwh_total":sum(r["site_outside_06_18_kwh"] for r in cohort if r["date"].startswith(m)),
          } for m in MONTHS
    },
    "published_reference":{
        k:reference[k] for k in ("legacy_full24_site_kwh","native_day12_inverters_kwh",
              "matched_day12_site_kwh","site_outside_06_18_kwh","legacy_absolute_diff_kwh",
              "aligned_absolute_diff_kwh")
    },
    "interpretation":{
       "source_channel_independence":"NOT ESTABLISHED; waveform is a near-exact forward aggregate of three inverter streams",
       "historical_meter_agreement_claim":"REVIEW R40 graph and text; original 24h-vs-12h comparison mixes time supports",
       "missing_data_use":"Mask site aggregate together with upstream inverter when simulating upstream acquisition outage",
       "conditional_downstream_only_failure":"Site stream may help only if distinct downstream export path survives; not field-proven",
       "operational_CERTIFY":"NOT ADMITTED",
    },
}
csvfields=list(records[0])
with (OUT/"R40_SIM_GATE3_DAY_AGGREGATE_ONLY.csv").open("w",newline="",encoding="utf8") as f:
    writer=csv.DictWriter(f,fieldnames=csvfields);writer.writeheader()
    for row in records:
        writer.writerow({k:concise(v) if isinstance(v,float) else v for k,v in row.items()})
(OUT/"R40_SIM_GATE3_SOURCE_TIMEBASE.json").write_text(json.dumps(summary,sort_keys=True,indent=2),encoding="utf8")
(OUT/"R40_SIM_GATE3_README.md").write_text(
"""# Timebase and shared-lineage audit (development only)

A prior source-day cross-channel figure compared a 24-hour integral of site
power with a 06:00-18:00 integral of inverter power. This audit independently
replays that historical difference, re-integrates both sources over the same
06:00-18:00 support, and decomposes the old difference into out-of-window
site energy plus residual. The 15-min site power is near-identical to the
forward 3x5-min average of all three inverter streams on selected dates.

Consequently, site power is not admissible as independently surviving
evidence under an upstream inverter-data deletion counterfactual. Neither
the small corrected difference nor a surviving downstream export signal
certifies separate instrument calibration or actual failure resilience.

No R40 scientific content is changed by this development audit. Do not
open R41 or promote conditional crossmeter outputs into CERTIFY.
""",encoding="utf8")
print("R40_SIM_GATE3_RESULT",json.dumps(summary,sort_keys=True),flush=True)
