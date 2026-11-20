#!/usr/bin/env python3
"""106Amen R42: exhaustive within-source candidate count and equal-gap decision audit.

Run on original public MORE-EU OpenData CSV at a Git-blessed source identity:
  Solar Park Data -INACCESS/Array Power.csv
  Git blob SHA-1 5611277efdd581bb839ec380239846a43ebe0ba7

Research reproducibility only. Do not redistribute original CC BY-NC source rows.
Paper result gate: R22 35 fixed-grid cells unchanged, 79 admitted months,
3/4/7/10/14 candidate combinations fully enumerated independent of outcomes.
"""
import argparse, calendar, csv, hashlib, itertools, json, math
from collections import defaultdict
from pathlib import Path
import numpy as np

GIT_BLOB = "5611277efdd581bb839ec380239846a43ebe0ba7"
EXPECTED_GRID = {"0":[5,6,7,9,9,9,9],"0.025":[41,51,55,58,58,61,65],
                 "0.05":[35,41,45,49,49,50,51],"0.075":[14,23,25,28,28,31,31],
                 "0.1":[9,10,12,13,15,15,16]}
Q_VALUES=[0,.025,.05,.075,.1]
SIZE_SET=[3,4,7,10,14]

def git_blob_digest(content):
    return hashlib.sha1(f"blob {len(content)}\0".encode()+content).hexdigest()

def input_months(path):
    b=path.read_bytes()
    assert git_blob_digest(b)==GIT_BLOB, "Pinned original MORE-EU Git blob mismatch"
    daily={}
    with path.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.reader(f)
        headers=next(reader)
        assert len(headers)==15 and headers[0]=="Timestamp"
        count=0
        for parts in reader:
            count+=1
            assert len(parts)==15, (count,len(parts))
            ds,clock=parts[0].split()
            d,m,y=map(int,ds.split("/"))
            date=f"{2000+y:04d}-{m:02d}-{d:02d}"
            record=daily.setdefault(date,dict(n=0,clocks=set(),tot=np.zeros(14,dtype=float)))
            record["n"]+=1
            assert clock not in record["clocks"], ("duplicate_clock",date,clock)
            record["clocks"].add(clock)
            vals=np.array([float(t) for t in parts[1:]],dtype=float)
            assert np.isfinite(vals).all()
            record["tot"]+=vals
    assert count==280512, count
    months=defaultdict(list)
    for d,rec in daily.items():months[d[:7]].append((d,rec))
    accepted=[]
    for m,d in months.items():
        year,month=map(int,m.split("-"))
        ndays=calendar.monthrange(year,month)[1]
        if len(d)!=ndays or any(r["n"]!=96 or len(r["clocks"])!=96 for _,r in d):
            continue
        arr=np.stack([r["tot"] for _,r in sorted(d)])
        full=arr.sum(axis=0)
        pref=np.concatenate((np.zeros((1,14)),np.cumsum(arr,axis=0)),axis=0)
        keep=[]; lengths=[]; starts=[]
        for L in range(1,8):
            for s in range(ndays-L+1):
                keep.append(full-(pref[s+L]-pref[s]))
                lengths.append(L)
                starts.append(s+1)
        accepted.append({"month":m,"days":ndays,"full":full,
                         "keep":np.stack(keep),"lengths":np.array(lengths),"starts":np.array(starts)})
    accepted.sort(key=lambda z:z["month"])
    assert len(accepted)==79, len(accepted)
    return accepted,len(months),count

def qs_flag(vals,q,axis=-1):
    return vals >= (1-q)*np.max(vals,axis=axis,keepdims=True)-1e-10

def percentile(a,p):
    return float(np.quantile(a,p,method="linear"))

def run(source):
    months,n_all,nrows=input_months(Path(source))
    original_grid={str(q):[0]*7 for q in Q_VALUES}
    for z in months:
        for q in Q_VALUES:
            full=qs_flag(z["full"],q)
            gap=qs_flag(z["keep"],q)
            changed=np.any(gap!=full[None,:],axis=1)
            for i,L in enumerate(range(1,8)):
                original_grid[str(q)][i]+=int(np.any(changed[z["lengths"]<=L]))
    assert original_grid==EXPECTED_GRID,(original_grid,EXPECTED_GRID)
    print("R42_PINNED_SOURCE_AND_R22_35_CELLS_PASS",flush=True)

    combos={k:np.array(list(itertools.combinations(range(14),k)),dtype=int) for k in SIZE_SET}
    assert sum(len(x) for x in combos.values())==5799
    eligible={k:{"L3":np.zeros(len(v),dtype=np.int16),"L7":np.zeros(len(v),dtype=np.int16)} for k,v in combos.items()}
    rate={L:{"mixed_months":0,"all_flip_months":0,"any_flip_months":0,
             "flip_windows":0,"stable_windows":0,"total_windows":0,
             "oracle_constant_errors":0,"examples":[]} for L in (1,3,7)}
    check_count=0
    for z in months:
        full=z["full"];retained=z["keep"];sizes=z["lengths"]
        source_members=qs_flag(full,.05)
        change_all=np.any(qs_flag(retained,.05)!=source_members[None,:],axis=1)
        for L in (1,3,7):
            a=change_all[sizes==L]
            nflip=int(a.sum());nno=len(a)-nflip;line=rate[L]
            line["flip_windows"]+=nflip;line["stable_windows"]+=nno;line["total_windows"]+=len(a)
            line["oracle_constant_errors"]+=min(nflip,nno)
            line["any_flip_months"]+=int(nflip>0)
            line["all_flip_months"]+=int(nno==0)
            line["mixed_months"]+=int(nflip>0 and nno>0)
            if nflip>0 and nno>0 and len(line["examples"])<5:
                s=z["starts"][sizes==L]
                line["examples"].append({"month":z["month"],"start_changes":int(s[np.argmax(a)]),
                                         "start_preserves":int(s[np.argmin(a)]),
                                         "n_change":nflip,"n_preserve":nno})
        for k,idx in combos.items():
            base=qs_flag(full[idx],.05)
            state=qs_flag(retained[:,idx],.05)
            changes=np.any(state != base[None,:,:],axis=2)
            eligible[k]["L3"]+=np.any(changes[sizes<=3],axis=0).astype(np.int16)
            eligible[k]["L7"]+=np.any(changes,axis=0).astype(np.int16)
            # independent pure-Python crosscheck for three predetermined subset columns
            if z["month"] in (months[0]["month"],months[-1]["month"]):
                for a in sorted(set((0,len(idx)//2,len(idx)-1))):
                    chosen=idx[a].tolist()
                    mx=max(float(full[j]) for j in chosen)
                    b=tuple(j for j in chosen if float(full[j])>=.95*mx-1e-10)
                    for maxL in (3,7):
                        slow=False
                        for row,l in zip(retained,sizes):
                            if l>maxL:continue
                            maxval=max(float(row[j]) for j in chosen)
                            new=tuple(j for j in chosen if float(row[j])>=.95*maxval-1e-10)
                            if new!=b:slow=True;break
                        fast=bool(np.any(changes[sizes<=maxL,a]))
                        assert slow==fast,(z["month"],k,a,maxL)
                        check_count+=1
    out=[]
    for k in SIZE_SET:
        d=eligible[k]
        entry={"candidate_count":k,"n_distinct_subsets":len(combos[k]),"n_months":len(months)}
        for L in (3,7):
            arr=d[f"L{L}"]
            entry[f"L{L}"]={"median":percentile(arr,.5),"p10":percentile(arr,.1),
                             "p90":percentile(arr,.9),"min":int(arr.min()),"max":int(arr.max()),
                             "mean":float(np.mean(arr)),"no_fragile_month_subsets":int(np.sum(arr==0))}
        out.append(entry)
        print("R42_CANDIDATE_COUNT",json.dumps(entry,sort_keys=True),flush=True)
    assert out[-1]["L3"]["median"]==45 and out[-1]["L7"]["median"]==51
    assert rate[3]["mixed_months"]==43 and rate[3]["flip_windows"]==430
    results={"gate":"PASS_PINNED_ORIGINAL_REPLAY","source_git_blob":GIT_BLOB,
             "original_license":"CC BY-NC; original CSV excluded from delivery",
             "original_csv_rows":nrows,"source_calendar_months":n_all,
             "admitted_months":len(months),"grid_35_lock":original_grid,
             "method":"Exhaustive within-plant candidate-set membership q=5%; all k-subsets; common-day gaps",
             "subset_size_statistics":out,
             "same_missing_rate_retro_audit":rate,
             "slow_independent_assertions":check_count,
             "no_field_failure_inference":True,"not_independent_trials":True,"source_rows_redistributed":False}
    return results

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--source",required=True)
    a.add_argument("--out",default="R42_DERIVED_ONLY")
    ns=a.parse_args()
    result=run(ns.source)
    folder=Path(ns.out);folder.mkdir(parents=True,exist_ok=True)
    (folder/"R42_MORE_EU_SUBSET_AND_RATEONLY_SUMMARY.json").write_text(json.dumps(result,indent=2),encoding="utf8")
    with (folder/"R42_SUBSET_SIZE_SUMMARY.csv").open("w",newline="",encoding="utf8") as f:
        rows=result["subset_size_statistics"]
        cols=["candidate_count","n_distinct_subsets","n_months","L3_median","L3_p10","L3_p90","L3_min","L3_max","L7_median","L7_p10","L7_p90","L7_min","L7_max"]
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for r in rows:
            z={k:r[k] for k in cols[:3]}
            for L in (3,7):
                for key in ("median","p10","p90","min","max"):z[f"L{L}_{key}"]=r[f"L{L}"][key]
            w.writerow(z)
    print("R42_COMPLETE_SOURCE_VERIFIED",json.dumps({"source":GIT_BLOB,"baseline35":True,"n_months":79,"n_subsets":5799,"n_checks":result["slow_independent_assertions"],"same_rate_3day_mixed":rate[3]["mixed_months"]}),flush=True)
