#!/usr/bin/env python3
"""R26H: source-native HKUST inverter-to-panel capacity reconciliation (no decision outcomes)."""
from pathlib import Path
from collections import defaultdict
import csv,io,zipfile,re,json
base=Path("R26H_HKUST_CapacityGate");base.mkdir(exist_ok=True)
with zipfile.ZipFile("source/dataset_original_Zenodo10909062.zip") as z:
    ttl_path=next(p for p in z.namelist() if p.endswith(".ttl"))
    ttl=z.read(ttl_path).decode("utf-8","replace")
txt=(Path("gate")/"COLOCATED_MULTIPLE_INVERTER_MONTH_GATE.csv").read_text()
group_rows=list(csv.DictReader(txt.splitlines()))
subj={}
pat=re.compile(r"(?ms)^pvsystem:([^\s]+)\s+a\s+brick:([^\s;]+)\s*;\s*(.*?)(?=^pvsystem:|\Z)")
for m in pat.finditer(ttl):
    subj[m.group(1)]=(m.group(2),m.group(3))
norm=lambda t:re.sub(r'[^0-9a-z]','',str(t).lower())
ids=defaultdict(list)
for name in subj:ids[norm(name)].append(name)
def unique_id(text):
    found=ids.get(norm(text),[])
    return found[0] if len(found)==1 else None
def item_inv(fn):
    short=fn[:-4] if fn.endswith(".csv") else fn
    key=unique_id(short)
    result={"file":fn,"rdf_id":key,"module_name":None,"module_n":None,"module_rated_W":None,"installed_W":None,"status":"HOLD"}
    if not key or subj[key][0]!="Inverter":
        result["reason"]="No unique original RDF inverter node";return result
    txt=subj[key][1]
    links=re.findall(r"brick:hasPart\s+pvsystem:([^\s;]+)",txt)
    if len(links)!=1 or links[0] not in subj:
        result["reason"]="Inverter does not point to one unique module node";return result
    module=links[0];body=subj[module][1]
    nu=re.search(r'ext:number\s*\[\s*brick:value\s*([0-9]+)\s*\]',body)
    stc=re.search(r'ext:ratedPowerOutput\s*\[\s*brick:hasUnit\s+unit:W\s*;\s*brick:value\s*([0-9.]+)\s*\]',body)
    if not nu or not stc or subj[module][0]!="PV_Panel":
        result["reason"]="No unique numeric module count and W/module";return result
    n=int(nu.group(1));w=float(stc.group(1))
    result.update(module_name=module,module_n=n,module_rated_W=w,installed_W=n*w,status="SOURCE_DERIVED")
    return result
def rated_station(group):
    key=unique_id(group)
    if not key or subj[key][0]!="PV_Generation_System": return None,key
    m=re.search(r'ext:ratedPowerOutput\s*\[\s*brick:hasUnit\s+unit:KW\s*;\s*brick:value\s*([0-9.]+)\s*\]',subj[key][1])
    return (float(m.group(1))*1000 if m else None),key
records=[]
for g in group_rows:
    fns=g["files"].split(';')
    ivs=[item_inv(f) for f in fns]
    nom,stkey=rated_station(g["same_roof_group"])
    total=sum(x['installed_W'] or 0 for x in ivs)
    diff=None if nom is None else (total-nom)/nom
    status=("SOURCE_STC_CHECKED" if all(x['status']=="SOURCE_DERIVED" for x in ivs)
            and nom is not None and abs(diff)<=0.01 else "HOLD_CAPACITY_CROSSWALK")
    item={"group":g["same_roof_group"],"rdf_station":stkey,"inverters":len(fns),
          "source_months_with_common_144_slots":g["common_strict_months"],
          "months":g["common_months"],"station_rated_W":nom,
          "sum_inverter_module_dc_stc_W":total,"relative_discrepancy":diff,
          "status":status,"devices":ivs}
    records.append(item)
    print("GROUP_RESULT",json.dumps(item),flush=True)
(base/"COLOCATED_RATED_CAPACITY_CROSSWALK.json").write_text(json.dumps(records,indent=2))
with (base/"CAPACITY_GATE_TABLE.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["group","rdf_station","inverters","source_months_with_common_144_slots","months","station_rated_W","sum_inverter_module_dc_stc_W","relative_discrepancy","status"])
    w.writeheader();w.writerows([{k:x.get(k) for k in w.fieldnames} for x in records])
print("SOURCE_STC_GROUPS",sum(x['status']=="SOURCE_STC_CHECKED" for x in records),"of",len(records))
