#!/usr/bin/env python3
"""Acquire the publisher's public SolarMagix V2 CSV files, verify hashes and write a source manifest.

Independent source-intake only. Does not change or execute any locked R25/R22 result.
Dataset DOI: 10.17632/4zgsckxpdy.2 (CC BY 4.0)
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request

ID = "4zgsckxpdy"
VERSION = 2
BASE = f"https://api.data.mendeley.com/datasets/{ID}"
OUT = Path("SolarMagix_V2_original")
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "ACQUISITION_STATUS.txt"
NAMES = {
    "stations.csv", "devices.csv", "source.csv",
    "hourly_pv_weather_inverter.csv", "hourly_pv_weather_station.csv",
    "energy_production_hourly_inverter.csv", "energy_production_hourly_station.csv",
    "energy_production.csv", "inverter_state_canonical.csv",
    "inverter_state_mapping_fusionsolar.csv", "inverter_state_mapping_solis.csv",
    "fusionsolar_energy_production.csv", "solis_energy_production.csv",
}

def log(msg):
    msg = str(msg)
    print(msg, flush=True)
    with LOG.open("a", encoding="utf-8") as f: f.write(msg + "\n")

def req(url):
    return urllib.request.Request(url, headers={
        "User-Agent": "SolarMagix-Acquisition-R26E/1.0 (academic reproducibility)",
        "Accept": "application/json,application/vnd.mendeley-public-dataset.1+json,*/*",
    })

def json_get(url, max_tries=3):
    for i in range(max_tries):
        try:
            with urllib.request.urlopen(req(url), timeout=65) as r:
                b = r.read()
                log(f"GET {url.split('?')[0]} => HTTP {r.status}, {len(b)} bytes")
                return json.loads(b)
        except Exception as ex:
            log(f"GET error attempt {i+1}: {url}: {str(ex)[:350]}")
            if i == max_tries-1: raise
            time.sleep(2 ** i)

def find_files(data):
    if isinstance(data, list): return data
    if not isinstance(data, dict): return []
    for k in ("files", "results", "items"):
        if isinstance(data.get(k), list): return data[k]
        if isinstance(data.get(k), dict):
            e = find_files(data[k])
            if e: return e
    return []

def file_name(obj):
    return obj.get("filename") or obj.get("name") or obj.get("file_name") or obj.get("key")

def save_file(meta, name):
    fid = meta.get("id") or meta.get("file_id")
    detail = meta.get("content_details") or {}
    download_url = detail.get("download_url") or meta.get("download_url")
    if not download_url:
        if not fid: raise RuntimeError(f"{name}: missing file UUID")
        download_url = f"{BASE}/files/{fid}/file_downloaded?version={VERSION}"
    # URLs come from publisher API or are constructed from its publisher file UUIDs.
    if not (download_url.startswith("https://") and (
         "mendeley.com/" in download_url or "elsevier.com/" in download_url
         or "amazonaws.com/" in download_url or "blob.core.windows.net/" in download_url)):
        raise RuntimeError(f"Unrecognized source host for {name} (do not follow arbitrary download URL)")
    target = OUT / name
    h = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(req(download_url), timeout=240) as r, target.open("wb") as w:
        log(f"DOWNLOAD {name}: HTTP {r.status} from publisher-provided URL")
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk: break
            w.write(chunk)
            h.update(chunk)
            size += len(chunk)
    if size < 10: raise ValueError(f"{name}: unexpectedly empty")
    expected_size = detail.get("size") or meta.get("size")
    expected_hash = detail.get("sha256_hash") or meta.get("sha256_hash")
    if expected_size is not None and int(expected_size) != size:
        raise ValueError(f"{name}: bytes mismatch expected {expected_size} got {size}")
    if expected_hash and str(expected_hash).lower() != h.hexdigest().lower():
        raise ValueError(f"{name}: SHA-256 differs from publisher")
    with target.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        count = sum(1 for _ in reader)
    log(f"VERIFIED {name}: {size} bytes, {count} rows, SHA256 {h.hexdigest()}")
    return dict(name=name, bytes=size, rows=count, columns=header, sha256=h.hexdigest(),
                publisher_sha256=expected_hash, publisher_size=expected_size, file_id=fid,
                publisher_hash_verified=bool(expected_hash))

def main():
    log(f"SolarMagix version {VERSION}, DOI 10.17632/{ID}.{VERSION}, source CC BY 4.0")
    metadata = None
    files = []
    for endpoint in [
        f"{BASE}?version={VERSION}",
        f"{BASE}/files?version={VERSION}",
        f"https://api.data.mendeley.com/datasets/publics/{ID}/files?version={VERSION}",
    ]:
        try:
            j = json_get(endpoint)
            if endpoint.endswith(f"{ID}?version={VERSION}"): metadata = j
            (OUT / ("publisher_dataset_metadata.json" if "/files?" not in endpoint else
                    "publisher_file_listing_" + str(len(files)) + ".json")).write_text(
                json.dumps(j, indent=2, ensure_ascii=False), encoding="utf-8")
            fs = find_files(j)
            if fs:
                log(f"LIST {len(fs)} publisher files from {endpoint}")
                if len(fs) >= len(files): files = fs
        except Exception as ex: log(f"Metadata endpoint unavailable: {ex}")
    if not files: raise RuntimeError("Mendeley API supplied no public file list; no raw data obtained")
    entries = {}
    for f in files:
        name = file_name(f)
        if name in NAMES:
            entries[name] = f
        elif name:
            log(f"IGNORED unrecognized dataset member: {name}")
    missing = sorted(NAMES - set(entries))
    log(f"Publisher-listed requested CSVs={len(entries)}/{len(NAMES)} missing={missing}")
    if missing: raise RuntimeError("Source file list incomplete; no claim of full acquisition")
    rows = []
    for name in sorted(NAMES):
        rows.append(save_file(entries[name], name))
    manifest = dict(dataset="SolarMagix", version=VERSION,
        doi=f"10.17632/{ID}.{VERSION}", citation="Daskalov and Zdravevski (2026), Mendeley Data V2",
        license="CC BY 4.0", provider="Mendeley Data", acquisition_method="public publisher API",
        raw_redistribution="Publisher-authored CSVs acquired byte-for-byte as downloaded; attribution required",
        source_files=rows, total_files=len(rows), total_bytes=sum(x["bytes"] for x in rows))
    (OUT / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with (OUT / "SOURCE_SHA256SUMS.txt").open("w") as f:
        for row in rows: f.write(f"{row['sha256']}  {row['name']}\n")
    log("COMPLETE PASS: publisher 13/13 files downloaded, provider size/hash (where stated), CSV readable.")
if __name__ == "__main__":
    try: main()
    except Exception as ex:
        log(f"ACQUISITION HOLD: {type(ex).__name__}: {ex}")
        sys.exit(1)
