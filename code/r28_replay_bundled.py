#!/usr/bin/env python3
"""Replay R28 from bundled R26I/R26K source-derived inputs; no imputation."""
from __future__ import annotations
import csv,json,shutil,subprocess,sys
from pathlib import Path
R=Path.cwd()
def readcsv(p):
    with Path(p).open(newline="",encoding="utf8") as f:
        return list(csv.DictReader(f))
i=R/"r28_evidence/HKUST_R26I"; k=R/"r28_evidence/HKUST_R26K"; p=R/"r28_evidence/R28_Primary"
assert i.is_dir() and k.is_dir() and p.is_dir()
(R/"input").mkdir(exist_ok=True)
(R/"source").mkdir(exist_ok=True)
(R/"primary").mkdir(exist_ok=True)
for base,name,target in [
    (i,"DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv","DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv"),
    (i,"SOURCE_BASED_TIER_REGISTER.csv","SOURCE_BASED_TIER_REGISTER.csv"),
    (i,"CALCULATION_CERTIFICATE.json","CALCULATION_CERTIFICATE.json"),
    (k,"SOURCE_MONTH_EPSILON_BASELINE_GATE.csv","R26K_SOURCE_MONTH_EPSILON_BASELINE_GATE.csv")]:
    shutil.copyfile(base/name,R/"input"/target)
shutil.copyfile(i/"DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv",R/"source/DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv")
for name in ("R28_CRITICAL_EPSILON_MONTHS.csv","R28_CRITICAL_MARGIN_CERTIFICATE.json","R28_EXPLICIT_CRITICAL_GAIN_WITNESSES.json"):
    shutil.copyfile(p/name,R/"primary"/name)
subprocess.run([sys.executable,"code/r28_critical_relative_gain.py"],check=True,stdout=subprocess.DEVNULL)
subprocess.run([sys.executable,"code/r28_independent_gain_ratio_qa.py"],check=True,stdout=subprocess.DEVNULL)
gold=readcsv(p/"R28_CRITICAL_EPSILON_MONTHS.csv")
out=readcsv("R28_CriticalGainMargin/R28_CRITICAL_EPSILON_MONTHS.csv")
assert len(gold)==len(out)==12
for a,b in zip(gold,out):
    assert (a["group"],a["month"],a["critical_status"])==(b["group"],b["month"],b["critical_status"])
    for key in ("relaxation_lower_bound","certified_witness_epsilon"):
        assert a[key]==b[key] or (a[key] and b[key] and abs(float(a[key])-float(b[key]))<5e-8)
ac=json.loads(Path("R28_CriticalGainMargin/R28_CRITICAL_MARGIN_CERTIFICATE.json").read_text())
ic=json.loads(Path("R28_IndependentCriticalQA/R28_INDEPENDENT_VERIFIER_CERTIFICATE.json").read_text())
assert ac["LP_calls"]==9360 and ac["witnesses"]==9 and ac["month_checks"]==12
assert ic["analytic_two_inverter_months"]==8 and ic["three_inverter_explicit_witness_months"]==4
assert ac["exclude_Qatar_QEERI"] and ic["no_qatar"]
print("R28_FULL_OFFLINE_REPLAY_PASS",json.dumps({"months":12,"LP_calls":9360,"witnesses":9,"independent_two_inverter":8,"explicit_three_inverter_witnesses":4,"original_thresholds_reproduced":True}))
