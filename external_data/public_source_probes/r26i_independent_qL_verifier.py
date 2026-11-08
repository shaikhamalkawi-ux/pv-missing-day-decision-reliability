#!/usr/bin/env python3
"""R26I independent brute-force verifier for development-only HKUST surfaces.
Reads only separately recorded daily numbers and original group-month result CSV.
No original raw dataset required for independent arithmetic audit.
"""
import csv,datetime as dt,calendar,collections,json
from pathlib import Path
P=Path("R26I_HKUST_SourceConditional")
def read(n):
    return list(csv.DictReader((P/n).open(encoding="utf8",newline="")))
daydata=read("DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv")
records=read("GROUP_MONTH_DECISION_GRID.csv")
aggregate=read("CONDITIONAL_GROUP_SURFACES.csv")
assert len(records)>0 and len(daydata)>0
per=collections.defaultdict(dict)
nominal=collections.defaultdict(dict)
for r in daydata:
    group,month,d,f=r["group"],r["month"],r["date"],r["inverter"]
    key=(group,month)
    assert int(r["source_slots"])==144
    assert f not in per[key].get(d,{}),("duplicate",key,d,f)
    per[key].setdefault(d,{})[f]=float(r["normalized_observed_sample_sum"])
    stc=float(r["device_module_dc_stc_W"]);p=float(r["sum_measured_power_W"])
    assert stc>0 and abs(p/stc-float(r["normalized_observed_sample_sum"]))<1e-8
    nominal[key][f]=stc
def choice(totals,q):
    mx=max(totals.values())
    assert mx>0
    return tuple(sorted(f for f in totals if totals[f]>=(1-q)*mx))
index={}
for r in records:
    k=(r["group"],r["month"],float(r["q"]),int(r["L"]))
    assert k not in index
    index[k]=r
qa=(0.,.025,.05,.075,.10)
checked=0
for (g,m),data in sorted(per.items()):
    n=calendar.monthrange(*map(int,m.split("-")))[1]
    dates=[f"{m}-{i:02d}" for i in range(1,n+1)]
    assert set(dates)==set(data),("month coverage",g,m)
    names=sorted(nominal[(g,m)])
    assert len(names)>=2
    assert all(set(data[d])==set(names) for d in dates)
    full={f:sum(data[d][f] for d in dates) for f in names}
    for q in qa:
        baseline=choice(full,q)
        for L in range(1,8):
            altered=[]
            for ln in range(1,L+1):
                for start in range(0,n-ln+1):
                    retained=dates[:start]+dates[start+ln:]
                    if len(retained)<10:continue
                    sums={f:sum(data[d][f] for d in retained) for f in names}
                    new=choice(sums,q)
                    if new!=baseline:altered.append((ln,dates[start],dates[start+ln-1],';'.join(new)))
            outcome=int(bool(altered))
            key=(g,m,q,L)
            assert key in index,key
            rec=index[key]
            assert int(rec["changed"])==outcome,(key,rec,outcome)
            assert rec["reference_shortlist"]==";".join(baseline)
            expected=min(altered) if altered else None
            assert rec["first_witness_len"]==(str(expected[0]) if expected else "")
            assert rec["first_witness_start"]==(expected[1] if expected else "")
            assert rec["first_witness_end"]==(expected[2] if expected else "")
            assert rec["witness_shortlist"]==(expected[3] if expected else "")
            checked+=1
assert checked==len(index),(checked,len(index))
for a in aggregate:
    key=(a["group"],float(a["q"]),int(a["L"]))
    members=[x for k,x in index.items() if k[0]==key[0] and k[2]==key[1] and k[3]==key[2]]
    assert members and len(members)==int(a["source_months"])
    assert sum(int(x["changed"]) for x in members)==int(a["fragile_count"])
for g in {x["group"] for x in records}:
    for m in {x["month"] for x in records if x["group"]==g}:
        for q in qa:
            states=[int(index[(g,m,q,L)]["changed"]) for L in range(1,8)]
            assert states==sorted(states),(g,m,q)
summary={"pass":True,"independent_bruteforce_month_qL_checks":checked,"aggregate_cells_verified":len(aggregate),
         "month_groups_checked":len(per),"source": "daily inverter measurement sums from R26I first pass",
         "frozen_R22_grid":list(qa),"L":list(range(1,8)),
         "no_qatar_data":True,"no_R25_changes":True}
(P/"INDEPENDENT_ARITHMETIC_VERIFICATION.json").write_text(json.dumps(summary,indent=2))
print("R26I independent verification PASS",json.dumps(summary),flush=True)
