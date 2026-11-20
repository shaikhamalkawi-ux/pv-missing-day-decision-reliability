#!/usr/bin/env python3
"""106Amen R46: PVDAQ 9068 paired-source eligibility and Honda public-access probe.

Research-only initial source check, never operational validation. All source raw
files stay in the transient runner; GitHub artifacts contain only JSON summaries.
Never infer wiring, capacity, independent hardware/clock from numeric similarity.
"""
import csv,datetime as dt,hashlib,json,math,re,urllib.request,urllib.error
from collections import Counter,defaultdict
from pathlib import Path
from statistics import median
from urllib.parse import quote

ROOT="https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/9068_OEDI/"
FILES={
"ac_power":"data/9068_ac_power_data_20240101_20250430.csv",
"meter":"data/9068_meter_data_20240101_20250430.csv",
"metadata":"metadata/9068_system_metadata.json"
}
OUT=Path("R46_PVDAQ9068_HONDA_SOURCE_EVIDENCE");OUT.mkdir(exist_ok=True)
RAW=Path("R46_PRIVATE_SOURCE_CACHE");RAW.mkdir(exist_ok=True)
def fetch(name,path):
    src=ROOT+path; dst=RAW/Path(path).name;h=hashlib.sha256();n=0
    req=urllib.request.Request(src,headers={"User-Agent":"106Amen-R46-reproducible-source-gate/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r, dst.open("wb") as f:
        for b in iter(lambda:r.read(2<<20),b""):
            h.update(b);n+=len(b);f.write(b)
    print("R46_FETCH_OK",name,n,h.hexdigest(),flush=True)
    return dst,dict(url=src,sha256=h.hexdigest(),bytes=n)
def short(x):
    if isinstance(x,dict):return {k:short(v) for k,v in list(x.items())[:10]}
    if isinstance(x,list):return [short(y) for y in x[:6]]
    return x if isinstance(x,(str,int,float,bool,type(None))) else str(x)
def read_meta(p):
    m=json.loads(p.read_text())
    out={"keys":list(m) if isinstance(m,dict) else None,"details":{}}
    if isinstance(m,dict):
        for k,v in m.items():
            if any(w in k.lower() for w in ("system","inverter","module","meter","metrics","mount","site")):
                info={"count":len(v) if hasattr(v,"__len__") else None,
                      "sample":short(v)}
                out["details"][k]=info
                print("R46_METADATA",k,json.dumps(info,default=str)[:4000],flush=True)
    return out
def parse(t):
    return dt.datetime.fromisoformat(t.strip().replace("Z","+00:00"))
def get_num(s):
    try:
        n=float(s.strip())
        return n if math.isfinite(n) else None
    except (ValueError,AttributeError):return None
def read_csv(p,kind):
    data={}; invalid=Counter(); n=0; months=Counter(); times=Counter();dups=0
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        rdr=csv.DictReader(f)
        headers=rdr.fieldnames
        timecol="measured_on" if "measured_on" in headers else headers[0]
        if kind=="ac_power":
            inverter=[h for h in headers if re.search(r"inverter_[12]_ac_power",h)]
            modules=[h for h in headers if re.search(r"inverter_module_",h) and "ac_power" in h]
            selected=inverter+modules
        else:
            inverter=[];modules=[];selected=[h for h in headers if "meter_ac_power_(kw)" in h and "phase" not in h]
        print("R46_CSV_HEADER",kind,json.dumps({"columns":headers,"select_totals":inverter,"module_channels":modules,"meter_main":selected if kind=="meter" else []}),flush=True)
        assert selected,("No comparable power channels",kind)
        for row in rdr:
            n+=1
            t=parse(row[timecol]);k=t.isoformat()
            if k in data:dups+=1;continue
            vals={}
            for field in selected:
                x=get_num(row.get(field,""))
                vals[field]=x
                if x is None:invalid[field]+=1
            data[k]=vals;months[t.strftime("%Y-%m")]+=1
            times[t.strftime("%H:%M")]+=1
    print("R46_CSV_SCAN",kind,json.dumps({"rows":n,"time_unique":len(data),"dups":dups,"months":dict(sorted(months.items())),"invalid":invalid,"sample_hour_counts":dict(list(times.items())[:5])},default=int)[:10000],flush=True)
    return data,{"rows":n,"duplicates":dups,"columns":headers,"inverter_totals":inverter,"module_channels":modules,"selected":selected,"invalid":dict(invalid),"month_counts":dict(sorted(months.items()))}
def quant(a,p):
    a=sorted(a)
    if not a:return None
    z=(len(a)-1)*p;i=int(z)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(z-i)
def compare(ac,acinfo,meter,minfo):
    mt=minfo["selected"][0];invcols=acinfo["inverter_totals"]
    both=set(ac).intersection(meter)
    residuals=[];signed=[];flagging=Counter();valid=[]
    for t in both:
        m=meter[t][mt]
        arr=[ac[t].get(c) for c in invcols]
        count=sum(x is None for x in arr)
        if m is None:flagging["meter_nonfinite"]+=1;continue
        flagging[f"missing_inverter_totals_{count}"]+=1
        if count:continue
        if sum(arr)>5 and m>5:
            d=m-sum(arr);signed.append(d);residuals.append(abs(d))
            valid.append((m,sum(arr)))
    qa={"aligned_timestamps":len(both),"n_inverter_totals":len(invcols),
    "missing_pattern":dict(flagging),"positive_daylight_complete":len(residuals),
    "median_abs_meter_vs_sum_kw":median(residuals) if residuals else None,
    "p95_abs_meter_vs_sum_kw":quant(residuals,.95),
    "median_signed_kw":median(signed) if signed else None,
    "m_sample_positive":len(valid),
    "meter_sum_relative_median_percent":median([100*abs(a-b)/min(a,b) for a,b in valid]) if valid else None,
    "meter_not_equated_to_independent_ground_truth":True}
    print("R46_PAIR_GATE",json.dumps(qa,sort_keys=True),flush=True)
    return qa
def probe_honda():
    urlbase="https://datadryad.org"
    tests=[
    ("dataset_metadata","/api/v2/datasets/doi%3A10.5061%2Fdryad.73n5tb363"),
    ("raw_file_metadata","/api/v2/files/3910978"),
    ("readme_file_metadata","/api/v2/files/3910982"),
    ("readme_public_download","/downloads/file_stream/3910982"),
    ("readme_api_download","/api/v2/files/3910982/download")
    ]
    out={}
    for name,path in tests:
        try:
            req=urllib.request.Request(urlbase+path,
                    headers={"User-Agent":"106Amen-R46-source-audit/1.0","Accept":"application/json" if "metadata" in name else "*/*","Range":"bytes=0-2047"})
            with urllib.request.urlopen(req,timeout=25) as r:
                data=r.read(2048)
                out[name]={"status":r.status,"bytes_read":len(data),"content_type":r.headers.get("Content-Type"),
                           "content_length":r.headers.get("Content-Length"),"sha256_read_prefix":hashlib.sha256(data).hexdigest()}
        except urllib.error.HTTPError as e:out[name]={"status":e.code,"error":str(e)[:100]}
        except Exception as e:out[name]={"status":"ERROR","error":type(e).__name__+":"+str(e)[:150]}
        print("R46_HONDA_ACCESS",name,json.dumps(out[name]),flush=True)
    return out
def main():
    results={"gate":"R46_SOURCE_AND_PAIR_ADMISSION","not_a_scientific_outcome":True,
        "raw_data_redistributed":False,"files":{}}
    for name,path in FILES.items():
        try:
            p,stamp=fetch(name,path);results["files"][name]=dict(status="PASS",**stamp)
            if name=="metadata":results["hardware"]=read_meta(p)
            elif name=="ac_power":a,ainfo=read_csv(p,name);results["ac_scan"]=ainfo
            elif name=="meter":m,minfo=read_csv(p,name);results["meter_scan"]=minfo
        except Exception as e:
            results["files"][name]={"status":"FAIL","url":ROOT+path,
                                   "error":type(e).__name__+": "+str(e)[:300]}
            print("R46_FETCH_FAIL",name,results["files"][name]["error"],flush=True)
    if all(results["files"][k]["status"]=="PASS" for k in FILES):
        results["paired_gate"]=compare(a,ainfo,m,minfo)
    results["honda"]=probe_honda()
    results["claim_boundary"]="Source presence and numerical channel agreement only, no demonstrated meter independence, missing-yield truth, or field-safe shortlist."
    (OUT/"R46_SOURCE_AND_PAIR_EVIDENCE.json").write_text(json.dumps(results,indent=2,default=str))
    print("R46_SOURCE_GATE_DONE",json.dumps({k:v["status"] for k,v in results["files"].items()}),flush=True)
if __name__=="__main__":main()
