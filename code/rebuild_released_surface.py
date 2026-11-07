#!/usr/bin/env python3
"""Validate the released publication surface from rights-safe tables."""
from pathlib import Path
import csv, json
ROOT=Path(__file__).resolve().parents[1]
combined=list(csv.DictReader(open(ROOT/'results/R22_DECISION_RELIABILITY_SURFACE.csv',encoding='utf-8')))
for ds, n in [('PROPRE.MA',25),('EURAC',7),('MORE-EU',79)]:
    rows=[r for r in combined if r['dataset']==ds]
    if len(rows)!=35: raise SystemExit(f'{ds}: expected 35 q x L cells, got {len(rows)}')
    if {int(float(r['months'])) for r in rows}!={n}: raise SystemExit(f'{ds}: month denominator mismatch')
    for q in sorted({float(r['q']) for r in rows}):
        seq=[int(float(r['fragile_by_L'])) for r in sorted((x for x in rows if abs(float(x['q'])-q)<1e-12),key=lambda x:int(float(x['gap_days'])))]
        if any(b<a for a,b in zip(seq,seq[1:])): raise SystemExit(f'{ds} q={q}: surface not monotone in L')
print('Released q x L surface: PASS')
cert=json.load(open(ROOT/'results/R22_RESULT_CERTIFICATE.json',encoding='utf-8'))
print('R22 certificate:', 'PASS' if cert.get('r21_q5_gap_le3_crosscheck_all_pass') else 'FAIL')
