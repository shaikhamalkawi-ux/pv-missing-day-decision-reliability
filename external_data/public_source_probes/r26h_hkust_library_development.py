#!/usr/bin/env python3
"""R26H development only: unmodified R22 shortlist q×L rule on source-admitted HKUST Library inverters.

Cohort and STC values independently source-gated before reading this outcome.
Not part of R25, not a pooled PV probability, no intrinsic technology claim.
"""
import collections,csv,datetime as dt,hashlib,io,json,math,zipfile
from pathlib import Path
out=Path("R26H_HKUST_Library_Development");out.mkdir(exist_ok=True)
zpath=Path("source/dataset_original_Zenodo10909062.zip")
h=hashlib.sha256()
with zpath.open("rb") as f:
    for c in iter(lambda:f.read(2*1024*1024),b''):h.update(c)
assert h.hexdigest()=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
with open("capacity/COLOCATED_RATED_CAPACITY_CROSSWALK.json") as f:caps=json.load(f)
a=[x for x in caps if x["group"]=="Library"]
assert len(a)==1 and a[0]["status"]=="SOURCE_STC_CHECKED"
devices=a[0]["devices"]
assert len(devices)==3
stcs={x["file"]:float(x["installed_W"]) for x in devices}
assert abs(sum(stcs.values())-float(a[0]["station_rated_W"]))<1e-8
months=a[0]["months"].split(';')
assert months==["2022-07","2023-05","2023-07"],months
source={}
within={}
with zipfile.ZipFile(zpath) as z:
    files=[x for x in z.namelist() if x.endswith(".csv") and Path(x).name in stcs]
    assert len(files)==3,files
    for fname in files:
        name=Path(fname).name
        perday=collections.defaultdict(list)
        with z.open(fname) as f:
            rdr=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",errors="replace"))
            assert "totalActivePower(W)" in rdr.fieldnames
            for row in rdr:
                t=row["Time"]
                ym=t[:7]
                if ym not in months:continue
                p=float(row["totalActivePower(W)"])
                perday[t[:10]].append((t,p))
        source[name]=perday
        within[name]=dict(rows=sum(map(len,perday.values())),negative=sum(p<0 for v in perday.values() for t,p in v),
              extreme_1p2x=sum(p>1.2*stcs[name] for v in perday.values() for t,p in v),
              missing=0,stc_W=stcs[name])
names=sorted(stcs)
days={}
for ym in months:
    dates=sorted(d for d in (source[names[0]].keys() & source[names[1]].keys() & source[names[2]].keys()) if d.startswith(ym))
    assert len(dates) in (30,31), (ym,dates)
    assert all(d.startswith(ym) for d in dates)
    for name in names:
        assert {d for d in source[name] if d.startswith(ym)}==set(dates)
        for d in dates:
            r=source[name][d]
            assert len(r)==144 and len({t for t,p in r})==144,(name,d)
            assert all(math.isfinite(p) for t,p in r)
    days[ym]=[(d,{name:sum(p for t,p in source[name][d])/stcs[name] for name in names}) for d in dates]
def shortlist(totals,q):
    best=max(totals.values())
    return tuple(sorted(k for k,v in totals.items() if v >= (1-q)*best))
qvals=[0,0.025,0.05,0.075,0.10]
results=[]
for ym in months:
    entries=days[ym]; dnames=[x[0] for x in entries];n=len(entries)
    for q in qvals:
        full={name:sum(row[1][name] for row in entries) for name in names}
        base=shortlist(full,q)
        for L in range(1,8):
            witnesses=[]
            for length in range(1,L+1):
                for st in range(n-length+1):
                    retain=[row for i,row in enumerate(entries) if not(st<=i<st+length)]
                    if len(retain)<10:continue
                    vals={name:sum(row[1][name] for row in retain) for name in names}
                    if shortlist(vals,q)!=base:
                        witnesses.append((length,dnames[st],dnames[st+length-1]))
            results.append(dict(month=ym,day_count=n,q=q,L=L,
                changed=int(bool(witnesses)),baseline=';'.join(base),
                min_witness_days=(min(x[0] for x in witnesses) if witnesses else ''),
                witness_start=(sorted(witnesses)[0][1] if witnesses else ''),
                witness_end=(sorted(witnesses)[0][2] if witnesses else '')))
assert len(results)==3*5*7
for month in months:
    for q in qvals:
        sequence=[r["changed"] for r in results if r["month"]==month and r["q"]==q]
        assert sequence==sorted(sequence),("L monotonicity",month,q)
with (out/"R26H_HKUST_LIBRARY_Q_L_DEVELOPMENT.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(results[0].keys()));w.writeheader();w.writerows(results)
agg=[]
for q in qvals:
    for L in range(1,8):
        n=sum(r["changed"] for r in results if r["q"]==q and r["L"]==L)
        agg.append(dict(q=q,L=L,fragile_month_count=n,admitted_months=3,
                        descriptive_fraction=n/3))
with (out/"R26H_HKUST_LIBRARY_SURFACE.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(agg[0].keys()));w.writeheader();w.writerows(agg)
cert=dict(source="HKUST Zenodo 10909062",source_sha256=h.hexdigest(),
          station="Library only; other roof groups held by station-vs-module DC STC crosswalk",
          modules=devices,months=months,daytime_source_clock="144 × 5-minute time samples from 06:00 through 17:55",
          power_metric="totalActivePower(W); AC, numerators summed over observed samples, denominator module DC STC",
          counts_at_q5={f"L<={L}":sum(r["changed"] for r in results if r["q"]==0.05 and r["L"]==L) for L in (1,3,7)},
          source_quality=within,source_cohort_size=3,source_development_only=True,
          r25_locked_unchanged=True,claim_boundary="Source-specific, site-dependent, observed-inverter shortlist: not population risk, operational outage likelihood, technology superiority, or new generic robustness")
(out/"R26H_HKUST_LIBRARY_EXPLORATORY_CERTIFICATE.json").write_text(json.dumps(cert,indent=2))
print("RESULT_CERTIFICATE",json.dumps(cert),flush=True)
