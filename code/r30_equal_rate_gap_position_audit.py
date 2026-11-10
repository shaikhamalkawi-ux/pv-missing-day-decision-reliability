#!/usr/bin/env python3
"""R30 independent exact-seven-day HKUST equal-missingness contrast."""
import csv,json
from pathlib import Path
from collections import defaultdict
root=Path(__file__).resolve().parent.parent
inp=root/"r28_evidence/HKUST_R26I/DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv"
with inp.open(newline="",encoding="utf8") as f: records=list(csv.DictReader(f))
days_data=defaultdict(dict)
for row in records:
    if row["group"]=="Library" and row["month"]=="2023-07":
        day=row["date"];inv=row["inverter"]
        assert inv not in days_data[day]
        days_data[day][inv]=float(row["normalized_observed_sample_sum"])
days=sorted(days_data);keys=tuple(sorted(days_data[days[0]]))
assert len(days)==31 and len(keys)==3
assert all(tuple(sorted(days_data[d]))==keys for d in days)
q=.10
def setof(v):
    top=max(v.values())
    assert top>0
    return tuple(k for k in keys if v[k]>=(1-q)*top)
total={k:sum(days_data[d][k] for d in days) for k in keys}
baseline=setof(total);assert len(baseline)==3
rows=[]
for i in range(25):
    removed=days[i:i+7]
    keep=[d for d in days if d not in removed]
    after=setof({k:sum(days_data[d][k] for d in keep) for k in keys})
    alt=setof({k:total[k]-sum(days_data[d][k] for d in removed) for k in keys})
    assert after==alt
    rows.append({"first_day":removed[0],"last_day":removed[-1],"deleted_days":7,
                 "retained_days":len(keep),"changed":after!=baseline,"after":list(after)})
flip=[r for r in rows if r["changed"]];stable=[r for r in rows if not r["changed"]]
expected=[("2023-07-05","2023-07-11"),("2023-07-07","2023-07-13"),("2023-07-08","2023-07-14")]
assert len(rows)==25 and len(flip)==3 and len(stable)==22
assert [(r["first_day"],r["last_day"]) for r in flip]==expected
assert len(flip[0]["after"])==2
assert rows[0]["first_day"]=="2023-07-01" and not rows[0]["changed"]
res={"status":"PASS","scope":"counterfactual_7_day_windows_not_observed_outage_history",
     "source":"HKUST original Zenodo 10909062 source-derived R26I complete Library days",
     "roof":"Library","month":"2023-07","q":q,"deleted_days":7,"total_complete_days":31,
     "window_count":25,"changed_window_count":3,"unchanged_window_count":22,
     "full_month_shortlist":list(baseline),"inverter_names":list(keys),
     "changed_windows":flip,"unchanged_example":rows[0],
     "method_agreement":"retained-sum_vs_full-minus-omitted_PASS",
     "not_probability":True,"not_independent_trials":True,"qatar_qeeri":False}
(root/"results/R30_HKUST_SAME_RATE_GAP_POSITION_CERTIFICATE.json").write_text(json.dumps(res,indent=2)+"\n")
with (root/"results/R30_HKUST_SAME_RATE_ALL_25_WINDOWS.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=["first_day","last_day","deleted_days","retained_days","changed","after"]);w.writeheader()
    for a in rows:w.writerow({**a,"after":"|".join(a["after"])})
print("R30_EQUAL_RATE_GAP_AUDIT_PASS",json.dumps({"window_count":25,"changed":3,"unchanged":22,"q":q,"deleted_days":7}))
