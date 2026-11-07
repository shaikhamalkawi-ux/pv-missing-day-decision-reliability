#!/usr/bin/env python3
import csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
rows = list(csv.DictReader(open(ROOT/'results/R22_DECISION_RELIABILITY_SURFACE.csv', encoding='utf-8')))

def get(ds,q,L):
    for r in rows:
        if r.get('dataset')==ds and abs(float(r['q'])-q)<1e-12 and int(float(r['gap_days']))==L:
            return int(float(r['fragile_by_L'])), int(float(r['months']))
    raise KeyError((ds,q,L))
expected = {'PROPRE.MA': (3,25),'EURAC': (1,7),'MORE-EU': (45,79)}
for ds, exp in expected.items():
    got = get(ds,0.05,3)
    if got != exp: raise SystemExit(f'{ds}: expected {exp}, got {got}')
    print(ds, 'PASS', got)
cert = json.load(open(ROOT/'results/R22_RESULT_CERTIFICATE.json', encoding='utf-8'))
if not cert.get('r21_q5_gap_le3_crosscheck_all_pass'): raise SystemExit('R22 certificate does not report cross-stage PASS')
print('R22 certificate PASS')
