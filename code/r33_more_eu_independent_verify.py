#!/usr/bin/env python3
"""Second, float-based implementation verifying pinned MORE-EU exact-q bands.

No import of primary exact-q engine. Independently parses the original source,
re-aggregates daily array output, tests every reported band's midpoint via
direct retained-day summation, and replays all 35 locked R22 grid cells.
"""
import csv,calendar,json,sys
from collections import defaultdict,Counter
from datetime import datetime
from pathlib import Path
P=Path(sys.argv[1])
D=json.loads(Path("R33_MORE_EU_EXACTQ_SOURCE_CERTIFICATE.json").read_text())
grid=[0.0,.025,.05,.075,.10]
rows=defaultdict(lambda:{"times":set(),"count":0,"vals":[0.]*14})
with P.open(newline="",encoding="utf-8-sig") as f:
    reader=csv.reader(f);assert len(next(reader))==15
    for row in reader:
        dt=datetime.strptime(row[0],"%d/%m/%y %H:%M");val=[float(z) for z in row[1:]]
        d=rows[dt.date().isoformat()];d["count"]+=1;d["times"].add((dt.hour,dt.minute))
        for k,z in enumerate(val):d["vals"][k]+=z
months=defaultdict(dict)
for d,v in rows.items():months[d[:7]][d]=v
admitted={}
for month,days in months.items():
    y,m=map(int,month.split("-"))
    if len(days)==calendar.monthrange(y,m)[1] and all(x["count"]==96 and len(x["times"])==96 for x in days.values()):
        admitted[month]={d:x["vals"] for d,x in days.items()}
assert len(admitted)==79
locked={}
with open("results/R22_DECISION_RELIABILITY_SURFACE.csv",newline="") as f:
    for x in csv.DictReader(f):
        if x["dataset"]=="MORE-EU":locked[(float(x["q"]),int(x["gap_days"]))]=int(x["fragile_by_L"])
assert len(locked)==35
def shortlist(z,q):
    mx=max(z)
    return tuple(j for j,a in enumerate(z) if a>=(1-q)*mx-1e-11)
counts=Counter();tested=0;blind=0;grid_cells=0
certby={r["month"]:r for r in D["per_month"]}
assert len(certby)==79
for month,days in sorted(admitted.items()):
    ds=sorted(days);n=len(ds)
    assert month in certby
    v=[days[d] for d in ds]
    full=[sum(day[j] for day in v) for j in range(14)]
    windows=[]
    for L in range(1,8):
        for i in range(n-L+1):
            # Independently sum only retained rows (not full-minus-missing).
            kept=[sum(v[t][j] for t in range(n) if not (i<=t<i+L)) for j in range(14)]
            windows.append((L,kept))
    rec=certby[month]
    assert len(windows)==rec["gap_windows"]
    for q in grid:
        base=shortlist(full,q)
        for L in range(1,8):
            counts[(q,L)]+=int(any(shortlist(w,q)!=base for d,w in windows if d<=L))
            grid_cells+=1
    for band in rec["intervals"]:
        a=float(band["lower_pct"])/100.;b=float(band["upper_pct"])/100.
        q=(a+b)/2.
        assert 0<=a<b<=.10000000000001
        assert any(shortlist(w,q)!=shortlist(full,q) for d,w in windows),(month,q)
        if band["grid_blind"]:
            assert all(not (a<=q0<b) for q0 in grid),(month,band)
            blind+=1
        tested+=1
    # Fixed points outside exact-q bands must be stable.
    for q in (.000234,.010567,.039123,.069456,.098765):
        active=any(a["lower_pct"] and float(a["lower_pct"])/100<=q<float(a["upper_pct"])/100 for a in rec["intervals"])
        direct=any(shortlist(w,q)!=shortlist(full,q) for _,w in windows)
        assert active==direct,(month,q,active,direct)
for k,value in counts.items():
    assert value==locked[k],("R22 count disagreement",k,value,locked[k])
assert tested==D["all_fragility_bands"] and blind==D["grid_blind_bands"]
assert grid_cells==79*35
report={"status":"PASS_INDEPENDENT_MORE_EU_FROM_PINNED_ORIGINAL",
  "independent_months":79,"independent_grid_cells_monthwise":grid_cells,
  "historical_grid_source_cells":len(locked),
  "tested_band_midpoints":tested,"verified_hidden_band_midpoints":blind,
  "pinned_source_blob":D["original_git_blob"],
  "q5_L3":counts[(.05,3)],"no_imputation":True,"Qatar_QEERI":False}
Path("R33_MORE_EU_INDEPENDENT_QA.json").write_text(json.dumps(report,indent=2)+"\n")
print("R33_MORE_EU_INDEPENDENT_PASS",json.dumps(report))
