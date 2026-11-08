#!/usr/bin/env python3
"""Download SolarMagix V2 from Mendeley public web Download All URL (no API token)."""
import csv, hashlib, json, os
from pathlib import Path, PurePosixPath
import shutil, sys, urllib.request, urllib.error, zipfile, urllib.parse

DATASET="4zgsckxpdy"
VERSION=2
SOURCE="https://data.mendeley.com/datasets/4zgsckxpdy/2"
ZIP_URL=f"https://data.mendeley.com/public-api/zip/{DATASET}/download/{VERSION}"
ROOT=Path("SolarMagix_V2_Publisher")
ROOT.mkdir(exist_ok=True)
ARCHIVE=ROOT/"SolarMagix_V2_DownloadAll_PUBLISHER.zip"
LOG=ROOT/"ACQUISITION_STATUS.txt"
EXPECTED = {
    "stations.csv", "devices.csv", "source.csv", "hourly_pv_weather_inverter.csv",
    "hourly_pv_weather_station.csv", "energy_production_hourly_inverter.csv",
    "energy_production_hourly_station.csv", "energy_production.csv",
    "inverter_state_canonical.csv", "inverter_state_mapping_fusionsolar.csv",
    "inverter_state_mapping_solis.csv", "fusionsolar_energy_production.csv",
    "solis_energy_production.csv",
}
def log(t):
    print(t,flush=True)
    with LOG.open("a",encoding="utf-8") as f: f.write(str(t)+"\n")
def get(url):
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (research-archive-source-verification; academic)",
        "Accept":"application/zip,application/octet-stream,*/*",
        "Referer": SOURCE,
    })
    return urllib.request.urlopen(req,timeout=120)
def main():
    log(f"SOURCE: {SOURCE} DOI:10.17632/4zgsckxpdy.2, CC BY 4.0")
    log(f"DOWNLOAD ENDPOINT (from public Mendeley JS button): {ZIP_URL}")
    digest=hashlib.sha256(); bcount=0
    with get(ZIP_URL) as r, ARCHIVE.open("wb") as f:
        log(f"HTTP {r.status}, FINAL_HOST={urllib.parse.urlparse(r.url).hostname}, CONTENT_TYPE={r.headers.get('content-type')}, DECLARED_BYTES={r.headers.get('content-length')}")
        while 1:
            x=r.read(2*1024*1024)
            if not x: break
            f.write(x); bcount+=len(x);digest.update(x)
    log(f"PROVIDER ZIP bytes={bcount}, SHA256={digest.hexdigest()}")
    with ARCHIVE.open("rb") as f:
        if f.read(4)[:2]!=b"PK":
            log("NONZIP response beginning was not archive magic; download rejected")
            raise RuntimeError("Publisher public download returned non-ZIP bytes")
    with zipfile.ZipFile(ARCHIVE) as z:
        infos=z.infolist()
        log(f"ZIP entries={len(infos)}")
        assert all(not x.is_dir() or x.filename.endswith("/") for x in infos)
        file_names={PurePosixPath(x.filename).name:x for x in infos if not x.is_dir()}
        log("Archive filenames: "+json.dumps(sorted(file_names.keys())))
        extra=sorted(set(file_names)-EXPECTED)
        missing=sorted(EXPECTED-set(file_names))
        if extra: log("EXTRA publisher archive members: "+str(extra))
        if missing: raise RuntimeError("Dataset lacks expected source CSVs: "+str(missing))
        bad=z.testzip()
        if bad: raise RuntimeError(f"ZIP CRC failure in {bad}")
        log("ZIP CRC PASS")
        records=[]
        for name in sorted(EXPECTED):
            info=file_names[name]
            if info.file_size>1024*1024*1024:
                raise RuntimeError("Member too large for this intake")
            target=ROOT/name
            h=hashlib.sha256();size=0
            with z.open(info) as inp,target.open("wb") as out:
                while 1:
                    x=inp.read(2*1024*1024)
                    if not x:break
                    size+=len(x);h.update(x);out.write(x)
            with target.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
                rdr=csv.reader(f); header=next(rdr,None);n=sum(1 for _ in rdr)
            records.append({"name":name,"size":size,"sha256":h.hexdigest(),"rows":n,
                            "columns":header,"original_zip_member":info.filename})
            log(f"{name}: bytes={size},rows={n},SHA256={h.hexdigest()}")
    out={"doi":"10.17632/4zgsckxpdy.2","source_url":SOURCE,"download_url":ZIP_URL,
         "license":"CC BY 4.0","publisher_zip_sha256":digest.hexdigest(),
         "publisher_zip_bytes":bcount,"files":records,"expected_files":len(EXPECTED),
         "status":"PASS: all CSVs and provider ZIP CRC; no scientific qxL test attempted",
         "note":"Original data remain distinct from locked project 106Amen R25/R22 scientific results"}
    (ROOT/"SOURCE_MANIFEST.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    with (ROOT/"SOURCE_SHA256SUMS.txt").open("w") as f:
        for x in records:f.write(x["sha256"]+"  "+x["name"]+"\n")
    log("COMPLETE: source capture and byte inspection passed")
if __name__=="__main__":
    try: main()
    except Exception as e:
        log(f"HOLD: {type(e).__name__}: {e}")
        sys.exit(1)
