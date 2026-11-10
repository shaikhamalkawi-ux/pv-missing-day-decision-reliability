#!/usr/bin/env python3
"""R29 independent log-gain difference-constraint verification, solver-free.

Each selected full-month/gap shortlist alternative is a finite set of
log(eta) difference constraints. Negative cycles imply infeasibility;
otherwise the minimum log spread is -min shortest-path distance.
See Supplement S4d. Data input is preserved source-derived HKUST daily
inverter yields, NOT raw third-party telemetry or device calibration.
"""
from collections import defaultdict
from itertools import product
from pathlib import Path
import csv, json, math

ROOT=Path(".")
EVIDENCE=ROOT/"r28_evidence"
OUTPUT=ROOT/"results"
OUTPUT.mkdir(exist_ok=True)
Q=.05; T=1-Q

def read_csv(file):
    with file.open(newline="",encoding="utf8") as f:
        return list(csv.DictReader(f))
daily=read_csv(EVIDENCE/"HKUST_R26I/DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv")
locked=read_csv(EVIDENCE/"R28_Primary/R28_CRITICAL_EPSILON_MONTHS.csv")
bykey={(x["group"],x["month"]):x for x in locked}
witnesses=json.loads((EVIDENCE/"R28_Primary/R28_EXPLICIT_CRITICAL_GAIN_WITNESSES.json").read_text())
witby={(x["group"],x["month"]):x for x in witnesses}
source=defaultdict(lambda:defaultdict(dict))
for row in daily:
    source[(row["group"],row["month"])][row["date"]][row["inverter"]]=float(row["normalized_observed_sample_sum"])
assert len(source)==12 and len(bykey)==12 and len(witby)==9

def shortlist(y,eta):
    m=max(y[k]*eta[k] for k in y)
    assert m>0
    return tuple(sorted(k for k in y if y[k]*eta[k]>=(1-Q)*m))

def radius(names,edges):
    n=len(names); ix={v:i for i,v in enumerate(names)}
    d=[[0. if i==j else float("inf") for j in range(n)] for i in range(n)]
    for a,b,w in edges:
        i,j=ix[a],ix[b]
        d[i][j]=min(d[i][j],w)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                d[i][j]=min(d[i][j],d[i][k]+d[k][j])
    if any(d[i][i]<-1e-12 for i in range(n)):
        return None
    spread=max(0.,-min(min(row) for row in d))
    return math.tanh(spread/2)

def comparisons(full,gap,names,ref,j,k,assignment):
    edges=[]
    for a in ref:
        for b in names:
            if a!=b:edges.append((a,b,math.log(full[a]/(T*full[b]))))
    outsiders=[a for a in names if a not in ref]
    for a,b in zip(outsiders,assignment):
        edges.append((b,a,math.log(T*full[b]/full[a])))
    if j in ref:
        assert k and k!=j
        edges.append((k,j,math.log(T*gap[k]/gap[j])))
    else:
        assert k is None
        for b in names:
            if j!=b:edges.append((j,b,math.log(gap[j]/(T*gap[b]))))
    return edges

out=[];graphs=0;max_difference=0.
for key,raw in sorted(source.items()):
    days=sorted(raw);names=sorted(raw[days[0]])
    assert len(days)==31 and len(names) in (2,3)
    assert all(sorted(raw[d])==names for d in days)
    full={a:sum(raw[d][a] for d in days) for a in names}
    ref=shortlist(full,{a:1. for a in names})
    outsiders=[a for a in names if a not in ref]
    choices=[tuple(b for b in names if b!=a) for a in outsiders]
    best=float("inf");count=0
    for span in (1,2,3):
        for first in range(32-span):
            gap={a:sum(raw[d][a] for d in days[:first]+days[first+span:]) for a in names}
            for assignment in product(*choices) if choices else [()]:
                for j in names:
                    rivals=[b for b in names if b!=j] if j in ref else [None]
                    for k in rivals:
                        count+=1
                        eps=radius(names,comparisons(full,gap,names,ref,j,k,assignment))
                        if eps is not None and eps<best:best=eps
    graphs+=count
    r=bykey[key]
    if r["relaxation_lower_bound"]:
        lp=float(r["relaxation_lower_bound"])
        diff=abs(best-lp)
        assert diff<5e-10,(key,best,lp)
        max_difference=max(max_difference,diff)
        w=witby[key]
        eta=w["eta"]
        assert shortlist(full,eta)==ref
        kept=[d for d in days if not(w["omitted_first"]<=d<=w["omitted_last"])]
        g={a:sum(raw[d][a] for d in kept) for a in names}
        assert shortlist(g,eta)!=ref
        assert best<=float(r["certified_witness_epsilon"])<.05
        status="LOWER_MATCHED_STRICT_UPPER_WITNESS"
    else:
        assert best>.05 and not r["certified_witness_epsilon"]
        status="NO_WITNESS_WITHIN_5PCT_GRAPH_CERTIFICATE"
    out.append({"group":key[0],"month":key[1],"devices":len(names),
                "graph_closed_epsilon":best,"previous_lp_relaxed_lower":r["relaxation_lower_bound"],
                "previous_lp_strict_upper":r["certified_witness_epsilon"],
                "graph_cases":count,"source_tier":r["tier"],"status":status})
assert graphs==4680 and len(out)==12
assert sum(x["status"]=="LOWER_MATCHED_STRICT_UPPER_WITNESS" for x in out)==9
assert sum(x["status"]=="NO_WITNESS_WITHIN_5PCT_GRAPH_CERTIFICATE" for x in out)==3
report={"status":"PASS_INDEPENDENT_GRAPH_CERTIFICATE","source_conditional":True,
        "LP_solver_imported":False,"months":12,"graphs":graphs,
        "original_strict_relaxed_LP_calls":9360,
        "nine_positive_lower_cases":9,"three_over_cap_cases":3,
        "max_abs_epsilon_graph_minus_LP":max_difference,
        "Qatar_QEERI":False,"records":out}
(OUTPUT/"R29_GRAPH_CERTIFICATE.json").write_text(json.dumps(report,indent=2)+"\n")
print("R29_GRAPH_CERTIFICATE_PASS",json.dumps({k:v for k,v in report.items() if k!="records"}))
