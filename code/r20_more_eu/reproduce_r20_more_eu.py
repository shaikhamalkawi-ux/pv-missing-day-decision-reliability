#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,itertools,calendar
from collections import defaultdict
from datetime import datetime
from pathlib import Path
ALPHA=0.95;N_ARRAYS=14
def shortlist(total):
    mx=max(total);return tuple(i+1 for i,v in enumerate(total) if v>=ALPHA*mx-1e-12)
def parse(path:Path):
    days={};bad_ts=bad_num=neg=over=rows=0;prev=None;gaps=0
    with path.open(newline='',encoding='utf-8-sig') as f:
        r=csv.reader(f);header=next(r)
        if len(header)!=15: raise ValueError(f'Expected 15 columns, got {len(header)}')
        for row in r:
            if not row:continue
            if len(row)!=15:bad_num+=1;continue
            try:dt=datetime.strptime(row[0],'%d/%m/%y %H:%M')
            except ValueError:bad_ts+=1;continue
            try:vals=[float(x) for x in row[1:]]
            except ValueError:bad_num+=1;continue
            neg+=sum(v<0 for v in vals);over+=sum(v>1.0000001 for v in vals)
            if prev is not None and (dt-prev).total_seconds()!=900:gaps+=1
            prev=dt;key=dt.date().isoformat();d=days.setdefault(key,{'date':dt.date(),'times':set(),'count':0,'sums':[0.0]*N_ARRAYS});d['count']+=1;d['times'].add((dt.hour,dt.minute))
            for j,v in enumerate(vals):d['sums'][j]+=v
            rows+=1
    return days,{'rows':rows,'bad_timestamp_rows':bad_ts,'bad_numeric_rows':bad_num,'negative_values':neg,'values_over_one':over,'global_non_15min_gaps':gaps}
def analyze(days):
    months=defaultdict(list)
    for d in days.values():months[(d['date'].year,d['date'].month)].append(d)
    out=[];incomplete=[]
    for (y,m),ds in sorted(months.items()):
        ds=sorted(ds,key=lambda x:x['date']);expected=calendar.monthrange(y,m)[1]
        if len(ds)!=expected or any(d['count']!=96 or len(d['times'])!=96 for d in ds):incomplete.append(f'{y:04d}-{m:02d}');continue
        total=[sum(d['sums'][j] for d in ds) for j in range(N_ARRAYS)];base=shortlist(total);counts={};min_k=None;witness=None;new_list=None
        for k in (1,2,3):
            c=0;first=None;first_list=None
            for idx in itertools.combinations(range(len(ds)),k):
                t=total.copy()
                for ix in idx:
                    for j in range(N_ARRAYS):t[j]-=ds[ix]['sums'][j]
                sl=shortlist(t)
                if sl!=base:c+=1;first=idx if first is None else first;first_list=sl if first_list is None else first_list
            counts[k]=c
            if min_k is None and c:min_k=k;witness=[ds[i]['date'].isoformat() for i in first];new_list=first_list
        leader=max(total);margin=min(abs(v/leader-ALPHA) for v in total);out.append({'month':f'{y:04d}-{m:02d}','days':len(ds),'baseline':'|'.join(map(str,base)),'min_k_le3':min_k,'changes_k1':counts[1],'changes_k2':counts[2],'changes_k3':counts[3],'closest_ratio_margin':margin,'witness':'|'.join(witness or []),'new_list':'|'.join(map(str,new_list or ()))})
    return out,incomplete
def main():
    ap=argparse.ArgumentParser();ap.add_argument('csv');ap.add_argument('outdir');a=ap.parse_args();out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True);days,qa=parse(Path(a.csv));rows,incomplete=analyze(days);fields=['month','days','baseline','min_k_le3','changes_k1','changes_k2','changes_k3','closest_ratio_margin','witness','new_list']
    with (out/'R20_MONTH_LOWK_SUMMARY.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    summary={**qa,'complete_months':len(rows),'incomplete_month_count':len(incomplete),'q':0.05,'min_retained_days':10,'one_day_fragile_months':sum(r['min_k_le3']==1 for r in rows),'two_day_fragile_months':sum(r['min_k_le3']==2 for r in rows),'three_day_fragile_months':sum(r['min_k_le3']==3 for r in rows),'no_change_through_3_days':sum(r['min_k_le3'] is None for r in rows),'incomplete_months':incomplete};(out/'R20_SUMMARY.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
