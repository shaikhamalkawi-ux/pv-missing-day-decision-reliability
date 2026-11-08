#!/usr/bin/env python3
"""Frozen public-source acquisition gate, Project 106Amen. No paper/result changes."""
import hashlib, json, pathlib, urllib.request, urllib.parse, sys, zipfile, subprocess
D = pathlib.Path("R26H_OfficialZenodoSourceIntake")
D.mkdir(exist_ok=True)
targets = [
    ("TECNALIA", "18306410", "TECNALIA.rar"),
    ("INES_CEA", "18316614", "INES-CEA.rar")
]
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"106Amen-source-vintage-verifier/1.0","Accept":"application/json,*/*"})
    return urllib.request.urlopen(req,timeout=100)
records=[]
for nickname, recid, filename in targets:
    entry={"dataset":nickname,"zenodo_record":recid,"filename":filename,"source_url":f"https://zenodo.org/records/{recid}","status":"HOLD"}
    try:
        with get(f"https://zenodo.org/api/records/{recid}") as f:
            raw=f.read()
        meta=json.loads(raw)
        (D/f"{nickname}_source_record.json").write_bytes(raw)
        matching=[x for x in meta.get("files",[]) if x.get("key")==filename]
        assert len(matching)==1, f"File not unique: {filename}"
        fm=matching[0]
        expected=fm.get("checksum","")
        expect_size=fm.get("size")
        url=fm.get("links",{}).get("self") or f"https://zenodo.org/api/records/{recid}/files/{filename}/content"
        assert url.startswith("https://zenodo.org/") or url.startswith("https://zenodo.org/api/")
        target=D/filename
        md5=hashlib.md5();sha=hashlib.sha256();n=0
        with get(url) as s,target.open("wb") as out:
            while True:
                chunk=s.read(1024*1024)
                if not chunk:break
                out.write(chunk);sha.update(chunk);md5.update(chunk);n+=len(chunk)
        entry.update(provider_checksum=expected,md5=md5.hexdigest(),sha256=sha.hexdigest(),size_bytes=n,provider_size=expect_size,doi=meta.get("pids",{}).get("doi",{}).get("identifier"),license=meta.get("metadata",{}).get("rights",[{}]))
        if expect_size is not None and int(expect_size)!=n:raise ValueError("Publisher size mismatch")
        if expected.startswith("md5:") and expected[4:].lower()!=md5.hexdigest():raise ValueError("Publisher MD5 mismatch")
        l=subprocess.run(["bsdtar","-tvf",str(target)],capture_output=True,text=True,timeout=90)
        (D/f"{nickname}_archive_listing.txt").write_text(l.stdout + "\nSTDERR:\n"+l.stderr)
        entry.update(archive_listing_status=l.returncode,list_sample=l.stdout.splitlines()[:12])
        if l.returncode !=0:raise RuntimeError("Archive listing failed")
        entry["status"]="PASS_SOURCE_BYTE_AND_ARCHIVE_LIST"
    except Exception as e:
        entry["issue"]=f"{type(e).__name__}: {str(e)[:450]}"
    records.append(entry)
    print(json.dumps(entry,default=str),flush=True)
(D/"INTAKE_MANIFEST.json").write_text(json.dumps(records,indent=2,default=str),encoding="utf-8")
if all(e["status"]=="PASS_SOURCE_BYTE_AND_ARCHIVE_LIST" for e in records):
    print("SOURCE INTAKE PASS, no empirical data claims",flush=True)
else:
    sys.exit("At least one official source acquisition is HOLD")
