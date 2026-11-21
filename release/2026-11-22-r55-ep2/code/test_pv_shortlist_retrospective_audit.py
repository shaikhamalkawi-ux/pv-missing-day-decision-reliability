#!/usr/bin/env python3
"""Standalone deterministic tests for the pedagogical R50 set-operation tool.
Synthetic arrays created in memory are test fixtures, NOT scientific PV observations.
"""
import calendar
from datetime import date
from decimal import Decimal
from pathlib import Path
import csv
import tempfile
from pv_shortlist_retrospective_audit import InputGateError, read_qualified_months, audit, run, shortlist

def toy(tmp, high_day=10):
    p=Path(tmp)/'synthetic_software_test.csv'
    with p.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['month','date','candidate','normalized_yield'])
        for d in range(1,29):
            ds=f'2026-02-{d:02d}'
            w.writerow(['2026-02',ds,'Array-A','10'])
            w.writerow(['2026-02',ds,'Array-B','14' if d==high_day else '9.4'])
    return p

with tempfile.TemporaryDirectory() as tmp:
    f=toy(tmp)
    m=read_qualified_months(f)
    cases,summary=audit(m,Decimal('0.05'),1,'SYNTHETIC_TEST')
    assert len(cases)==28
    assert summary[0]['days']==28 and summary[0]['candidates']==2
    assert summary[0]['complete_reference_shortlist']=='Array-A;Array-B'
    changes=[x for x in cases if x['changed']]
    assert len(changes)==1 and changes[0]['gap_start']=='2026-02-10'
    assert changes[0]['removed_candidates']=='Array-B' and not changes[0]['added_candidates']
    assert cases[0]['missing_day_pct']==cases[-1]['missing_day_pct']
    output=Path(tmp)/'out'
    meta=run(f,'SYNTHETIC_TEST','unitless pedagogical test yields',Decimal('.05'),3,output)
    assert meta['scenarios']==sum(28-L+1 for L in (1,2,3))
    assert (output/'scenario_membership_audit.csv').is_file()
    assert (output/'audit_scope_and_provenance.json').is_file()
    bad=Path(tmp)/'bad.csv'
    with f.open() as fi, bad.open('w') as fo:
        lines=fi.readlines();fo.writelines(lines[:-1])
    try:read_qualified_months(bad)
    except InputGateError:pass
    else:raise AssertionError('Missing candidate row should HOLD')
    duplicate=Path(tmp)/'duplicate.csv'
    with f.open() as fi, duplicate.open('w') as fo:
        lines=fi.readlines();fo.writelines(lines+[lines[1]])
    try:read_qualified_months(duplicate)
    except InputGateError:pass
    else:raise AssertionError('Duplicate record should HOLD')
    negatives=Path(tmp)/'negative.csv'
    with f.open() as fi, negatives.open('w') as fo:
        lines=fi.readlines();lines[1]=lines[1].replace('10','-1');fo.writelines(lines)
    try:read_qualified_months(negatives)
    except InputGateError:pass
    else:raise AssertionError('Negative yield should HOLD')
print('PUBLIC COMPLETE-MONTH SCRIPT: PASS (synthetic logic and negative input gates; not empirical replay)')
