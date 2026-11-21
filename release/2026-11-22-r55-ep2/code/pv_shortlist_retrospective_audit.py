#!/usr/bin/env python3
"""Reference implementation of the 106Amen retrospective PV shortlist deletion audit.

NOT a trained alarm, source-admission system, PV fault classifier, or certificate
of a correct decision under real missing data. Only use complete, already
quality-qualified daily normalized yields from one physical source at a time.

Usage:
  python pv_shortlist_retrospective_audit.py \
    --input qualified_complete_daily.csv \
    --source-id MY_SOURCE \
    --measurement-basis 'AC kWh/kWp DC-STC per source-day' \
    --q 0.05 --max-gap 3 --out output_dir

CSV schema: month,date,candidate,normalized_yield
  month: YYYY-MM
  date: YYYY-MM-DD (source calendar, NOT an inferred timezone)
  candidate: stable physical system/array/inverter ID
  normalized_yield: finite nonnegative daily sum in a common, source-qualified
                    and physically documented comparison basis

One candidate record is required for every calendar day of each complete month.
No imputation is attempted, and no candidate-specific/asynchronous gap is tested.
"""
from __future__ import annotations

import argparse
import calendar
import csv
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from pathlib import Path
import sys
from typing import Any

REQUIRED = ('month', 'date', 'candidate', 'normalized_yield')
VERSION = 'R50-story-application-1.0'

class InputGateError(ValueError):
    """Input fails a necessary completeness/identity/measurement contract."""


def decimal_in_range(raw: str, name: str, lo: str, hi: str) -> Decimal:
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise InputGateError(f'{name} must be a decimal number') from exc
    if not value.is_finite() or not Decimal(lo) <= value <= Decimal(hi):
        raise InputGateError(f'{name} must be finite and in [{lo}, {hi}]')
    return value


def read_qualified_months(input_csv: Path) -> dict[str, dict[date, dict[str, Decimal]]]:
    """Validate strict rectangular, complete source-months; no gap repairing."""
    if not input_csv.is_file() or not input_csv.stat().st_size:
        raise InputGateError('Missing or empty input CSV')
    groups: dict[str, dict[date, dict[str, Decimal]]] = defaultdict(lambda: defaultdict(dict))
    with input_csv.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or any(col not in reader.fieldnames for col in REQUIRED):
            raise InputGateError('Required columns: '+','.join(REQUIRED))
        for line,row in enumerate(reader, 2):
            month, ds, candidate = ((row.get(k) or '').strip() for k in ('month','date','candidate'))
            raw=(row.get('normalized_yield') or '').strip()
            if not month or not ds or not candidate or not raw:
                raise InputGateError(f'Line {line}: blank required field')
            try:
                day = date.fromisoformat(ds)
            except ValueError as exc:
                raise InputGateError(f'Line {line}: invalid ISO calendar date') from exc
            if not re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])', month):
                raise InputGateError(f'Line {line}: month must be YYYY-MM')
            if month != day.strftime('%Y-%m'):
                raise InputGateError(f'Line {line}: date is outside indicated month')
            y=decimal_in_range(raw,'normalized_yield','0','1e100')
            if candidate in groups[month][day]:
                raise InputGateError(f'Line {line}: duplicate {month}/{day}/{candidate}')
            groups[month][day][candidate]=y
    if not groups:
        raise InputGateError('No admissible rows')
    first_candidates=None
    for month,by_day in sorted(groups.items()):
        y, m=map(int,month.split('-'))
        n=calendar.monthrange(y,m)[1]
        expected={date(y,m,d) for d in range(1,n+1)}
        if set(by_day) != expected:
            missing=sorted(expected-set(by_day)); extraneous=sorted(set(by_day)-expected)
            raise InputGateError(f'{month}: incomplete full calendar month; missing days {missing[:4]}, extra {extraneous[:4]}')
        candidates=set(by_day[min(by_day)])
        if len(candidates) < 2:
            raise InputGateError(f'{month}: at least two distinct candidates are required')
        if first_candidates is None:
            first_candidates=candidates
        elif candidates!=first_candidates:
            raise InputGateError(f'{month}: candidate universe changed across months; audit separately')
        if any(set(row)!=candidates for row in by_day.values()):
            raise InputGateError(f'{month}: incomplete/asynchronous candidate-by-day rectangle')
        if max(sum(by_day[d][c] for d in by_day) for c in candidates)<=0:
            raise InputGateError(f'{month}: every candidate has zero monthly yield; screening ratio undefined')
    return groups


def shortlist(days: list[date], daily: dict[date,dict[str,Decimal]], q: Decimal) -> list[str]:
    candidates=sorted(daily[days[0]])
    totals={c:sum((daily[d][c] for d in days),Decimal(0)) for c in candidates}
    best=max(totals.values())
    if best<=0:
        raise InputGateError('Retained-day maximum yield is zero, cannot interpret near-best set')
    return [c for c in candidates if totals[c]>=(Decimal(1)-q)*best]


def audit(months: dict[str,dict[date,dict[str,Decimal]]], q: Decimal,
          max_gap:int, source_id:str)->tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    scenarios=[]; summaries=[]
    for month, daily in sorted(months.items()):
        days=sorted(daily)
        reference=shortlist(days,daily,q)
        changed=0; count=0
        for length in range(1,max_gap+1):
            if len(days)-length<10:
                continue
            for start in range(len(days)-length+1):
                omitted=days[start:start+length]
                retained=days[:start]+days[start+length:]
                selected=shortlist(retained,daily,q)
                a=sorted(set(selected)-set(reference))
                r=sorted(set(reference)-set(selected))
                different=bool(a or r)
                changed+=int(different);count+=1
                scenarios.append({
                    'source_id':source_id,'month':month,'q':str(q),
                    'gap_length':length,'gap_start':omitted[0].isoformat(),
                    'gap_end':omitted[-1].isoformat(),
                    'missing_day_pct':str((Decimal(100)*Decimal(length)/Decimal(len(days))).quantize(Decimal('0.0001'))),
                    'reference_shortlist':';'.join(reference),
                    'retained_shortlist':';'.join(selected),
                    'added_candidates':';'.join(a),'removed_candidates':';'.join(r),
                    'changed':int(different)
                })
        if count==0:
            raise InputGateError(f'{month}: no eligible deletion with >=10 retained days')
        summaries.append({
            'source_id':source_id,'month':month,'q':str(q),'max_gap_days':max_gap,
            'candidates':len(daily[days[0]]),'days':len(days),
            'eligible_deletions':count,'changed_deletions':changed,
            'fragile_at_least_once':int(changed>0),
            'complete_reference_shortlist':';'.join(reference),
            'interpretation':'RETROSPECTIVE_COMPLETE_REFERENCE_ONLY'
        })
    return scenarios,summaries


def write_csv(path:Path,rows:list[dict[str,Any]])->None:
    if not rows:
        raise InputGateError('Output rows are empty')
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)


def run(input_path:Path,source_id:str,measurement_basis:str,q:Decimal,max_gap:int,out:Path)->dict[str,Any]:
    if not source_id.strip() or not measurement_basis.strip():
        raise InputGateError('Source ID and measurement basis must be nonblank')
    if max_gap<1 or max_gap>7:
        raise InputGateError('This companion implements the declared L=1..7-day range only')
    months=read_qualified_months(input_path)
    sc,sm=audit(months,q,max_gap,source_id)
    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'scenario_membership_audit.csv',sc)
    write_csv(out/'month_fragility_summary.csv',sm)
    evidence={
        'version':VERSION,'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'source_id':source_id,'measurement_basis_as_supplied':measurement_basis,
        'q':str(q),'max_gap_days':max_gap,
        'input_contract':'Each day of each calendar month and each candidate must be present',
        'unit_normalization_and_source_admission':'USER RESPONSIBILITY - NOT VERIFIED BY SCRIPT',
        'missing_days':'Shared whole source-calendar days removed retrospectively; no imputation',
        'subsequent_review_flag_model':'NOT IMPLEMENTED',
        'field_outage_correctness':'NOT CERTIFIED',
        'months':len(sm),'scenarios':len(sc),'counts':{'changed_scenarios':sum(int(r['changed']) for r in sc),
                                                         'fragile_months':sum(int(r['fragile_at_least_once']) for r in sm)},
        'claim':'Retrospective set membership sensitivity conditional on the input data and declared rule.'
    }
    (out/'audit_scope_and_provenance.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return evidence


def main()->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input',required=True,type=Path)
    p.add_argument('--source-id',required=True)
    p.add_argument('--measurement-basis',required=True)
    p.add_argument('--q',default='0.05',help='Declared tolerance proportion (e.g. 0.05 = 5 percent)')
    p.add_argument('--max-gap',type=int,default=3,help='Maximum common whole days, 1-7')
    p.add_argument('--out',required=True,type=Path)
    args=p.parse_args()
    try:
        q=decimal_in_range(args.q,'q','0','0.10')
        result=run(args.input,args.source_id,args.measurement_basis,q,args.max_gap,args.out)
    except (InputGateError,OSError) as e:
        print('HOLD: '+str(e),file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2))
    return 0

if __name__=='__main__':
    sys.exit(main())
