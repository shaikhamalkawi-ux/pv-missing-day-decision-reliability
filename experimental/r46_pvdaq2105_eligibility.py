#!/usr/bin/env python3
"""R46 alternative site 2105 source-eligibility scan, before any decision test.
Read public PVDAQ S3 object listing, 2105 metadata and bounded CSV headers only.
No observations or unvalidated scientific results are distributed.
"""
import json,urllib.request,urllib.parse,urllib.error,xml.etree.ElementTree as ET,re,hashlib,csv,io
from pathlib import Path
ROOT="https://oedi-data-lake.s3.amazonaws.com"
PREFIX="pvdaq/2023-solar-data-prize/2105_OEDI/"
OUT=Path("R46_PVDAQ2105_SOURCE_SCAN");OUT.mkdir(exist_ok=True)
def fetch(url,limit=None):
 h={"User-Agent":"106Amen-R46-source-eligibility/1.0"}
 if limit:h["Range"]=f"bytes=0-{limit-1}"
 with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=30) as r:
  data=r.read(limit if limit else 2<<20)
  return data,{"http":r.status,"content_type":r.headers.get("Content-Type"),
    "content_range":r.headers.get("Content-Range"),"bytes_examined":len(data),
    "read_prefix_sha256":hashlib.sha256(data).hexdigest()}
def list_files():
 url=ROOT+"/?"+urllib.parse.urlencode({"list-type":"2","prefix":PREFIX,"max-keys":"250"})
 body,resp=fetch(url,2<<20)
 root=ET.fromstring(body)
 keys=[(e.findtext("{*}Key"),e.findtext("{*}Size")) for e in root.findall("{*}Contents")]
 print("R46_2105_LIST",json.dumps({"keys":keys[:150],"n":len(keys),"response":resp})[:20000],flush=True)
 return keys
def examine_meta():
 url=ROOT+"/"+PREFIX+"metadata/2105_system_metadata.json"
 body,resp=fetch(url,2<<20)
 m=json.loads(body)
 info={"uri":url,"sha256":hashlib.sha256(body).hexdigest(),"size":len(body),
       "keys":list(m),"summary":{}}
 for k,v in m.items():
  if any(t in k.lower() for t in ("system","module","inverter","meter","mount","site")):
   examples=list(v.values()) if isinstance(v,dict) else v if isinstance(v,list) else [v]
   info["summary"][k]={"count":len(examples),
      "samples":[{kk:vv for kk,vv in x.items() if kk in ("name","inverter_id","module_id","model","manufacturer","quantity","power(kW DC)","type","comments","public_name")} if isinstance(x,dict) else str(x)[:150] for x in examples[:3]]}
 print("R46_2105_METADATA",json.dumps(info)[:11000],flush=True)
 return info
def main():
 out={"site":"PVDAQ 2105","source_release":"DOE Solar Data Prize",
      "not_scientific_validation":True,"raw_rows_redistributed":False}
 try:files=list_files();out["files"]=files
 except Exception as e:
  out["list_error"]=repr(e)
  print("R46_2105_LIST_ERROR",repr(e),flush=True);files=[]
 try:out["metadata"]=examine_meta()
 except Exception as e:
  out["metadata_error"]=repr(e)
  print("R46_2105_META_ERROR",repr(e),flush=True)
 try:
  alt_body,alt_info=fetch(ROOT+"/"+PREFIX+"metadata/2105_system_metadata_v1.json",2<<20)
  alt=json.loads(alt_body)
  out["metadata_v1"]={"original_sha256":hashlib.sha256(alt_body).hexdigest(),
     "n_inverter_metadata":len(alt.get("Inverters",{})),
     "n_meter_metadata":len(alt.get("Meters",{})),
     "n_module_metadata":len(alt.get("Modules",{}))}
  print("R46_2105_META_V1",json.dumps(out["metadata_v1"]),flush=True)
 except Exception as e:
  out["metadata_v1_error"]=repr(e)
  print("R46_2105_META_V1_ERROR",repr(e),flush=True)
 # NOTE legacy except block below from replaced try starts a new syntactic unit
 try:
  pass
 except Exception:pass
 targets=[k for k,size in files if k and k.endswith(".csv") and "/data/" in k and
   (any(w in k.lower() for w in ("power","meter","inverter","electrical")) or ("/data/2105_inv" in k))]
 for key in targets[:10]:
  url=ROOT+"/"+urllib.parse.quote(key,safe="/")
  try:
   body,response=fetch(url,8192)
   hdr=body.split(b"\n",1)[0].decode("utf-8-sig","replace")[:1200]
   print("R46_2105_HEAD",key,hdr,flush=True)
   out.setdefault("header_probes",[]).append({"key":key,"header":hdr,**response})
  except Exception as e:
   out.setdefault("header_probes",[]).append({"key":key,"error":repr(e)})
 (OUT/"R46_PVDAQ2105_ELIGIBILITY.json").write_text(json.dumps(out,indent=2))
 print("R46_2105_DONE",json.dumps({"list_files":len(files),"metadata":bool(out.get("metadata")),"csv_headers_probed":len(out.get("header_probes",[]))}),flush=True)
if __name__=="__main__":main()
