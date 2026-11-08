#!/usr/bin/env python3
"""R26I HKUST group-source denominator and q×gap extension, development only.

Prospective admission: ≥2 co-located source-identifiable inverters; each inverter's
DC STC exactly recovered from all linked PV panel model nodes (count × W/module);
all devices share a complete source-clock month of 144 5-min timestamps 06–17:55
with finite recorded AC power for every source day. AC/DC station nameplate
mismatch is reported, never silently interpreted as a measurement error.
The original R22 {q}×{L} shortlist rule is unchanged. NO imputation.
No Qatar/QEERI records, no scientific R25 modification.
"""
import csv,io,hashlib,math,json,zipfile,re,calendar
from collections import defaultdict
from pathlib import Path
import datetime as dt
from rdflib import Graph, RDF, Namespace
OUT=Path("R26I_HKUST_SourceConditional"); OUT.mkdir(exist_ok=True)
source=Path("source/dataset_original_Zenodo10909062.zip")
sha=hashlib.sha256()
with source.open("rb") as f:
    for block in iter(lambda:f.read(2*1024*1024),b""):sha.update(block)
SOURCE_SHA="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
assert sha.hexdigest()==SOURCE_SHA, "Original source release checksum mismatch"
by_group=list(csv.DictReader(Path("gate/COLOCATED_MULTIPLE_INVERTER_MONTH_GATE.csv").open()))
assert len(by_group)==5, "Unexpected new/modified predeclared source groups"
expected_times={f"{h:02}:{m:02}:00" for h in range(6,18) for m in range(0,60,5)}
assert len(expected_times)==144
with zipfile.ZipFile(source) as z:
    assert z.testzip() is None
    tpath=next(x for x in z.namelist() if x.lower().endswith(".ttl"))
    turtle=z.read(tpath).decode("utf-8","replace")
    graph=Graph()
    graph.parse(data=turtle,format="turtle")
    ns=dict(graph.namespaces())
    BR=ns["brick"]; EX=ns["ext"]; PV=ns["pvsystem"]
    def local(ref):
        return str(ref)[len(str(PV)):] if str(ref).startswith(str(PV)) else str(ref)
    def normalize(x):return re.sub("[^a-z0-9]","",x.lower())
    nodes=defaultdict(list)
    for s in graph.subjects(RDF.type,None):
        if str(s).startswith(str(PV)):nodes[normalize(local(s))].append(s)
    def node(name):
        arr=list(set(nodes.get(normalize(name),[])))
        return arr[0] if len(arr)==1 else None
    def one_num(subject,predicate):
        links=list(graph.objects(subject,predicate))
        if len(links)!=1:return None
        vals=list(graph.objects(links[0],BR.value))
        if len(vals)!=1:return None
        try:return float(vals[0])
        except:return None
    def panel_info(panel):
        if (panel,RDF.type,BR.PV_Panel) not in graph:return None
        count=one_num(panel,EX.number)
        w=one_num(panel,EX.ratedPowerOutput)
        pp=list(graph.objects(panel,EX.ratedPowerOutput))
        units=list(graph.objects(pp[0],BR.hasUnit)) if len(pp)==1 else []
        if (count is None or w is None or len(units)!=1 or
            not str(units[0]).endswith(("W","/W","#W")) or count<=0 or count!=int(count) or
            not 1<=w<=1000):return None
        return dict(id=local(panel),module_count=int(count),rated_per_module_W=w,dc_stc_W=int(count)*w)
    def inverter_info(filename):
        n=node(filename[:-4])
        result=dict(filename=filename,source_node=local(n) if n is not None else None,status="HOLD",
                    linked_panels=[],module_dc_stc_W=None)
        if n is None or (n,RDF.type,BR.Inverter) not in graph:
            result["issue"]="No unique inverter RDF entity";return result
        parts=list(graph.objects(n,BR.hasPart))
        if not parts or len(set(parts))!=len(parts):
            result["issue"]="No panels or repeated panel links";return result
        panels=[panel_info(x) for x in parts]
        if any(p is None for p in panels):
            result["issue"]="One or more module panel links lack unique count/rating";return result
        result.update(linked_panels=panels,module_dc_stc_W=sum(x["dc_stc_W"] for x in panels),status="DERIVED_FROM_RDF")
        return result
    def site_meta(group):
        n=node(group)
        if n is None or (n,RDF.type,BR.PV_Generation_System) not in graph:return None,None
        num=one_num(n,EX.ratedPowerOutput)
        return local(n),(num*1000 if num is not None else None)
    records=[];eligible=[];summaries=[];daily_rows=[];decision_rows=[]; witness_rows=[]
    allpaths={Path(x).name:x for x in z.namelist() if x.lower().endswith(".csv")}
    for row in by_group:
        group=row["same_roof_group"]
        filenames=row["files"].split(";")
        source_months=row["common_months"].split(";") if row["common_months"] else []
        ivs=[inverter_info(f) for f in filenames]
        station_node,station_rated=site_meta(group)
        source_stcs=[x["module_dc_stc_W"] for x in ivs]
        dc_sum=sum(x for x in source_stcs if x is not None)
        status=("CONDITIONAL_RDF_DC_STC_ADMIT" if
                len(ivs)>=2 and source_months and all(x["status"]=="DERIVED_FROM_RDF" for x in ivs)
                else "HOLD_RDF_OR_TIME")
        meta=dict(group=group,station_rdf=station_node,source_station_rated_W=station_rated,
                  inverter_dc_stc_sum_W=dc_sum,station_to_dc_ratio=(station_rated/dc_sum if station_rated and dc_sum else None),
                  initial_source_clock_months=source_months,status=status,inverters=ivs)
        records.append(meta)
        if status!="CONDITIONAL_RDF_DC_STC_ADMIT":continue
        perfile={}
        for f in filenames:
            assert f in allpaths,(f,allpaths.keys())
            stc=next(x["module_dc_stc_W"] for x in ivs if x["filename"]==f)
            entries=defaultdict(dict)
            with z.open(allpaths[f]) as original:
                rd=csv.DictReader(io.TextIOWrapper(original,encoding="utf-8-sig",errors="replace"))
                assert "totalActivePower(W)" in rd.fieldnames and "Time" in rd.fieldnames
                for value in rd:
                    text=value["Time"].strip()
                    month=text[:7]
                    if month not in source_months:continue
                    if len(text)!=19 or text[10]!=" ":continue
                    date,clock=text.split(" ")
                    assert clock in expected_times, (group,f,text)
                    assert clock not in entries[date],(group,f,text)
                    try:p=float(value["totalActivePower(W)"])
                    except:p=float("nan")
                    entries[date][clock]=p
            perfile[f]=entries
        admitted=[];native_negative=0;native_overpower=0
        for month in source_months:
            yy,mm=map(int,month.split("-"))
            ndays=calendar.monthrange(yy,mm)[1]
            dates=[f"{month}-{d:02d}" for d in range(1,ndays+1)]
            for f in filenames:
                series=perfile[f]
                assert set(d for d in series if d.startswith(month))==set(dates),("source month days changed",group,f,month)
                for d in dates:
                    assert set(series[d])==expected_times,(group,f,month,d,len(series[d]))
                    assert len(series[d])==144 and all(math.isfinite(x) for x in series[d].values()),(group,f,month,d)
            admitted.append(month)
            daily={}
            for d in dates:
                vals={}
                for f in filenames:
                    stc=next(x["module_dc_stc_W"] for x in ivs if x["filename"]==f)
                    raw=list(perfile[f][d].values())
                    native_negative+=sum(x<0 for x in raw)
                    native_overpower+=sum(x>1.2*stc for x in raw)
                    power_sum=sum(raw)
                    vals[f]=power_sum/stc
                    daily_rows.append(dict(group=group,month=month,date=d,inverter=f,
                                           source_slots=len(raw),sum_measured_power_W=power_sum,
                                           device_module_dc_stc_W=stc,normalized_observed_sample_sum=vals[f],
                                           negative_samples=sum(x<0 for x in raw)))
                daily[d]=vals
            def decision(totals,q):
                M=max(totals.values())
                assert M>0
                return tuple(sorted(f for f in totals if totals[f] >= (1-q)*M))
            full={f:sum(daily[d][f] for d in dates) for f in filenames}
            qs=(0.,0.025,0.05,0.075,0.10)
            for q in qs:
                original=decision(full,q)
                for L in range(1,8):
                    found=[]
                    for length in range(1,L+1):
                        for first in range(ndays-length+1):
                            keep=[d for i,d in enumerate(dates) if not(first<=i<first+length)]
                            if len(keep)<10:continue
                            reduced={f:sum(daily[d][f] for d in keep) for f in filenames}
                            after=decision(reduced,q)
                            if after!=original:
                                found.append((length,dates[first],dates[first+length-1],';'.join(after)))
                    min_w=min(found) if found else None
                    decision_rows.append(dict(group=group,month=month,q=q,L=L,
                                              reference_shortlist=";".join(original),
                                              changed=int(bool(found)),first_witness_len=(min_w[0] if min_w else ""),
                                              first_witness_start=(min_w[1] if min_w else ""),
                                              first_witness_end=(min_w[2] if min_w else ""),
                                              witness_shortlist=(min_w[3] if min_w else "")))
        summaries.append(dict(group=group,months=len(admitted),month_list=";".join(admitted),
                              inverters=len(filenames),station_to_dc_ratio=meta["station_to_dc_ratio"],
                              negative_power_values=native_negative,
                              power_over_120pct_dc_samples=native_overpower))
    if not decision_rows:raise RuntimeError("No group passed source gate")
    for x in records:
        print("CAPACITY_GATE",json.dumps({k:v for k,v in x.items() if k!="inverters"}),flush=True)
    for x in summaries:print("ELIGIBLE_GROUP",json.dumps(x),flush=True)
    expected_count=sum(x["months"]*5*7 for x in summaries)
    assert len(decision_rows)==expected_count
    for x in summaries:
        for month in x["month_list"].split(";"):
            for q in (0.,0.025,0.05,0.075,0.10):
                seq=[r["changed"] for r in decision_rows if r["group"]==x["group"] and r["month"]==month and r["q"]==q]
                assert len(seq)==7 and seq==sorted(seq),("L monotonicity",x["group"],month,q)
    assert len([x for x in summaries if x["group"]=="Library"])==1
    lib=[r for r in decision_rows if r["group"]=="Library"]
    assert sum(r["changed"] for r in lib if r["q"]==0.05 and r["L"]==7)==0
    assert sum(r["changed"] for r in lib if r["q"]==0.10 and r["L"]==7)==1
    def save_csv(name,rows):
        with (OUT/name).open("w",newline="",encoding="utf8") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
            w.writeheader();w.writerows(rows)
    save_csv("GROUP_MONTH_DECISION_GRID.csv",decision_rows)
    save_csv("DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv",daily_rows)
    save_csv("CONDITIONAL_GROUP_COHORTS.csv",summaries)
    aggregate=[]
    for group in sorted({x["group"] for x in summaries}):
        for q in (0.,0.025,0.05,0.075,0.10):
            for L in range(1,8):
                records_=[r for r in decision_rows if r["group"]==group and r["q"]==q and r["L"]==L]
                count=sum(r["changed"] for r in records_)
                aggregate.append(dict(group=group,q=q,L=L,fragile_count=count,source_months=len(records_),
                                      descriptive_fraction=count/len(records_)))
    save_csv("CONDITIONAL_GROUP_SURFACES.csv",aggregate)
    (OUT/"RDF_DEVICE_CAPACITY_TRACE.json").write_text(json.dumps(records,indent=2),encoding="utf8")
    report=dict(status="PASS_DEVELOPMENT_ONLY",source="Zenodo 10909062",
                sha256=SOURCE_SHA,note="Five-minute source-observed AC production divided by module DC STC; no imputation",
                original_r25_untouched=True,eligible_groups=len(summaries),
                group_months=sum(x["months"] for x in summaries),decision_cells=len(decision_rows),
                aggregate_cells=len(aggregate),q5_l3={x["group"]:next((r["fragile_count"],r["source_months"]) for r in aggregate if r["group"]==x["group"] and r["q"]==0.05 and r["L"]==3) for x in summaries},
                caution="Capacity mismatch can reflect incomparable station/inverter rating bases; no causal or universal conclusions. Source resampling has NA but not filled; site/meter uncertainty and operation boundary remain uncalibrated.")
    (OUT/"CALCULATION_CERTIFICATE.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    print("R26I_CALC_CERT",json.dumps(report),flush=True)
