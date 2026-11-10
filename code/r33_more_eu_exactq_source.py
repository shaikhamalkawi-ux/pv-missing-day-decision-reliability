#!/usr/bin/env python3
"""Independent exact-q sweep for the pinned public MORE-EU source.
Raw INACCESS CC BY-NC data is fetched transiently, hashed and never archived.
No imputation, no QEERI; original R22 q*L values must match cell-for-cell.
"""
from __future__ import annotations
from collections import defaultdict, Counter
from datetime import datetime
from decimal import Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path
import calendar,csv,hashlib,json,sys
R=Path.cwd();QMAX=F(1,10);GRID=[F(0),F(1,40),F(1,20),F(3,40),QMAX]
DATA=Path(sys.argv[1]);EXPECTED_BLOB="5611277efdd581bb839ec380239846a43ebe0ba7"
def pct(x):
    with localcontext() as c:
        c.prec=28
        return str(Decimal(x.numerator)*100/Decimal(x.denominator))
def choose(v,q):
    m=max(v.values())
    assert m>0
    return tuple(sorted(k for k in v if v[k]>=(1-q)*m))
def git_hash(b):
    import hashlib
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def parse(path):
    assert git_hash(path.read_bytes())==EXPECTED_BLOB,"Original public Git blob changed"
    data=defaultdict(lambda:{"times":set(),"count":0,"vals":[Decimal(0)]*14})
    stats=Counter();prev=None
    with path.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.reader(f)
        head=next(reader);assert len(head)==15
        for row in reader:
            if len(row)!=15:stats["bad_row"]+=1;continue
            try:
                ts=datetime.strptime(row[0],"%d/%m/%y %H:%M")
                vals=[Decimal(s) for s in row[1:]]
            except Exception:stats["bad_numeric_or_timestamp"]+=1;continue
            if prev and (ts-prev).total_seconds()!=900:stats["non_15min_gap"]+=1
            prev=ts;stats["rows"]+=1
            if any(x<0 or x>1 for x in vals):stats["out_of_range"]+=1
            day=data[ts.date().isoformat()];day["count"]+=1
            day["times"].add((ts.hour,ts.minute))
            for j,x in enumerate(vals):day["vals"][j]+=x
    assert stats["rows"]==280512 and stats["bad_row"]==0 and stats["bad_numeric_or_timestamp"]==0
    assert stats["out_of_range"]==0 and stats["non_15min_gap"]==16,stats
    return data,dict(stats)
def accepted(data):
    months=defaultdict(dict)
    for d,v in data.items():months[d[:7]][d]=v
    accept={};rejected=[]
    for m,ds in sorted(months.items()):
        y,mo=map(int,m.split("-"))
        if len(ds)!=calendar.monthrange(y,mo)[1] or any(x["count"]!=96 or len(x["times"])!=96 for x in ds.values()):
            rejected.append(m);continue
        accept[m]={d:{str(j+1):F(v["vals"][j]) for j in range(14)} for d,v in ds.items()}
    assert len(accept)==79 and len(rejected)==18,(len(accept),len(rejected))
    return accept,rejected
def month_audit(month,observed):
    days=sorted(observed);names=sorted(observed[days[0]],key=int)
    assert len(names)==14 and len(days)>=28
    n=len(days);tot={k:sum(observed[d][k] for d in days) for k in names}
    th0={k:F(1)-tot[k]/max(tot.values()) for k in names}
    windows=[];atoms=[]
    for L in range(1,8):
        if n-L<10:continue
        for start in range(n-L+1):
            kept={k:tot[k]-sum(observed[d][k] for d in days[start:start+L]) for k in names}
            assert min(kept.values())>=0
            windows.append((L,start,kept))
            th={k:F(1)-kept[k]/max(kept.values()) for k in names}
            for k in names:
                a,b=th0[k],th[k]
                if a==b:continue
                lo=max(F(0),min(a,b));hi=min(QMAX,max(a,b))
                if lo<hi:atoms.append((lo,hi))
    merged=[]
    for lo,hi in sorted(atoms):
        if not merged or lo>merged[-1][1]:merged.append([lo,hi])
        elif hi>merged[-1][1]:merged[-1][1]=hi
    status={}
    for q in GRID:
        full=choose(tot,q)
        for L in range(1,8):
            status[(q,L)]=int(any(choose(v,q)!=full for ell,_,v in windows if ell<=L))
    # Endpoints (q=10% clipped) are explicitly checked against direct records.
    grid_blind=0
    for lo,hi in merged:
        middle=(lo+hi)/2
        assert any(choose(v,middle)!=choose(tot,middle) for _,_,v in windows)
        hits=[q for q in GRID if lo<=q<hi or (q==QMAX and hi==QMAX and any(choose(v,q)!=choose(tot,q) for _,_,v in windows))]
        if not hits:grid_blind+=1
    # Independent direct midpoints of some raw event cells; assert union identity.
    unique=sorted({F(0),QMAX}|{v for ab in atoms for v in ab})
    # Every 97th breakpoint and all five official grid points.
    tests=set(GRID)|{unique[k] for k in range(0,len(unique),97)}
    for q in tests:
        actual=any(choose(v,q)!=choose(tot,q) for _,_,v in windows)
        union=any(lo<=q<hi for lo,hi in merged)
        if q==QMAX:union=actual
        assert actual==union,(month,"endpoint",pct(q))
    for a,b in zip(unique[::max(1,len(unique)//11)],unique[1::max(1,len(unique)//11)]):
        if a>=b:continue
        q=(a+b)/2
        direct=any(choose(v,q)!=choose(tot,q) for _,_,v in windows)
        assert direct==any(lo<=q<hi for lo,hi in merged)
    return {"month":month,"days":n,"bands":len(merged),"grid_blind_bands":grid_blind,
            "q5_L3":status[(F(1,20),3)],"q5_L7":status[(F(1,20),7)],
            "gap_windows":len(windows),"atomic_events":len(atoms),
            "selected_exact_endpoints_verified":len(tests),
            "intervals":[{"lower_pct":pct(a),"upper_pct":pct(b),
                          "upper_at_domain_cap":b==QMAX,
                          "grid_blind":not any(a<=q<b or (q==QMAX and b==QMAX and any(choose(v,q)!=choose(tot,q) for _,_,v in windows)) for q in GRID)}
                         for a,b in merged]},status
def main():
    days,source=parse(DATA);months,rejected=accepted(days)
    locked={}
    with (R/"results/R22_DECISION_RELIABILITY_SURFACE.csv").open(newline="") as f:
        for x in csv.DictReader(f):
            if x["dataset"]=="MORE-EU":locked[(F(Decimal(x["q"])),int(x["gap_days"]))]=int(x["fragile_by_L"])
    assert len(locked)==35
    rows=[];counts=Counter();windows=0;events=0
    for m,month in months.items():
        obj,grid=month_audit(m,month);rows.append(obj)
        windows+=obj["gap_windows"];events+=obj["atomic_events"]
        for qL,flag in grid.items():counts[qL]+=flag
    assert len(rows)==79
    for k,v in counts.items(): assert v==locked[k],("R22 mismatch",k,v,locked[k])
    out={"status":"MORE_EU_EXACT_Q_SOURCE_LOCK_PASS",
         "source_repo":"MORE-EU/OpenData","original_git_blob":EXPECTED_BLOB,
         "source_license":"CC BY-NC (INACCESS / Power Factors), derived audit only",
         "source_rows":source["rows"],"source_non_15min_gaps":source["non_15min_gap"],
         "admitted_months":len(rows),"rejected_months":len(rejected),
         "admission_rule":"all calendar days 96 rows and unique quarter-hour clock labels",
         "qgrid_r22_cells_matching":len(counts),"q5_L3_fragile_months":counts[(F(1,20),3)],
         "months_with_blind_bands":sum(x["grid_blind_bands"]>0 for x in rows),
         "all_fragility_bands":sum(x["bands"] for x in rows),
         "grid_blind_bands":sum(x["grid_blind_bands"] for x in rows),
         "examined_gap_windows":windows,"atomic_events":events,
         "not_sensor_error_or_failure_probability":True,"imputation":False,
         "no_qatar_qeeri":True,"per_month":rows}
    target=R/"R33_MORE_EU_EXACTQ_SOURCE_CERTIFICATE.json"
    target.write_text(json.dumps(out,indent=2)+"\n")
    print("MORE_EU_EXACT_Q_PASS",json.dumps({k:v for k,v in out.items() if k!="per_month"}),flush=True)
if __name__=="__main__":main()
