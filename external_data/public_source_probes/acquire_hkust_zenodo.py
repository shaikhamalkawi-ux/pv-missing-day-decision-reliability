#!/usr/bin/env python3
"""Independent source archive audit: HKUST rooftop 60-station dataset, Zenodo 10909062.

This source-intake tool audits raw archive integrity and structure only.
It does NOT compute PV shortlist outcomes or alter the frozen R22/R25 manuscript.
"""
import hashlib, json, pathlib, csv, io, urllib.request, zipfile, sys, traceback
d=pathlib.Path("R26H_HKUST_Zenodo_SourceIntake");d.mkdir(exist_ok=True)
record="10909062"
site=f"https://zenodo.org/records/{record}"
url=f"https://zenodo.org/api/records/{record}"
def call(u):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"106amen-source-integrity/1.0","Accept":"*/*"}),timeout=180)
def log(s):
    print(s,flush=True)
    with (d/"ACQUISITION_STATUS.txt").open("a") as h:h.write(str(s)+"\n")
manifest={"reference":site,"record_id":record,"scientific_role":"CANDIDATE_ONLY","status":"HOLD"}
try:
    with call(url) as r:data=r.read()
    meta=json.loads(data)
    (d/"zenodo_record.json").write_bytes(data)
    files=meta.get("files",[])
    log("FILES: "+str([(x.get("key"),x.get("size"),x.get("checksum")) for x in files]))
    manifest["license"]=meta.get("metadata",{}).get("rights",[])
    manifest["doi"]=meta.get("pids",{}).get("doi",{}).get("identifier")
    names=[x.get("key","") for x in files]
    f=next(x for x in files if x.get("key","").lower()=="dataset.zip")
    url2=f.get("links",{}).get("self") or f"https://zenodo.org/api/records/{record}/files/{f['key']}/content"
    assert url2.startswith("https://zenodo.org/")
    name=f["key"]
    target=d/"dataset_original_Zenodo10909062.zip"
    hs=hashlib.sha256();hm=hashlib.md5();n=0
    with call(url2) as inp,target.open("wb") as out:
        while 1:
            v=inp.read(2*1024*1024)
            if not v:break
            out.write(v);hs.update(v);hm.update(v);n+=len(v)
            if n%(64*1024*1024) < len(v): log(f"DOWNLOADED {n:,} bytes")
    digest=f.get("checksum","")
    log(f"ZIP {n} bytes, SHA256 {hs.hexdigest()}, MD5 {hm.hexdigest()}")
    if f.get("size") is not None and int(f["size"])!=n:raise ValueError("size mismatch")
    if digest.startswith("md5:") and digest[4:].lower()!=hm.hexdigest():raise ValueError("publisher hash mismatch")
    with zipfile.ZipFile(target) as z:
        corrupt=z.testzip()
        if corrupt:raise ValueError("ZIP CRC mismatch: "+corrupt)
        info=[x for x in z.infolist() if not x.is_dir()]
        log(f"ZIP CRC PASS, {len(info)} members, uncompressed bytes {sum(x.file_size for x in info):,}")
        preview=[]
        for obj in info:
            p=obj.filename
            row={"filename":p,"uncompressed_bytes":obj.file_size,"compressed_bytes":obj.compress_size}
            if p.lower().endswith(('.csv','.txt','.ttl','.md')) and obj.file_size < 500000000:
                with z.open(obj) as inp:
                    v=inp.read(2500).decode("utf-8-sig","replace")
                row["head_excerpt"]=v[:600]
            preview.append(row)
    (d/"FILE_INVENTORY.json").write_text(json.dumps(preview,ensure_ascii=False,indent=2))
    manifest.update({"status":"PASS_ORIGINAL_ZIP_SOURCE_INTEGRITY","size":n,"sha256":hs.hexdigest(),"md5":hm.hexdigest(),
                     "publisher_md5":digest,"total_members":len(preview),
                     "total_uncompressed_bytes":sum(x["uncompressed_bytes"] for x in preview),
                     "zip_crc":"PASS","source_version":"Zenodo record 10909062; DO NOT assume byte parity with later Dryad Sept 2024"})
except Exception as exc:
    log("HOLD "+str(type(exc).__name__)+": "+str(exc))
    manifest["issue"]=str(exc)
(d/"SOURCE_MANIFEST.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False,default=str))
if manifest["status"].startswith("PASS"):log("SOURCE PASS; no PV result computed")
else:sys.exit(1)
