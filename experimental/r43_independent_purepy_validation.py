#!/usr/bin/env python3
"""Independent row-based implementation of the R43 MORE-EU time-holdout.
Original source is not reproduced in the output. Pure Python, no Numpy;
reconstruct retained-day yields by direct summation (not full-minus-gap).
This QA uses frozen expected outputs, NOT fit or threshold re-selection.
"""
import argparse,calendar,csv,hashlib,json,statistics
from collections import defaultdict
from pathlib import Path

PIN='5611277efdd581bb839ec380239846a43ebe0ba7'

def digest(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def pctl(a,p):
 a=sorted(a); pos=(len(a)-1)*p; i=int(pos)
 return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(pos-i)
def calc_auc(rows):
 pos=[v[0] for v in rows if v[1]]; neg=[v[0] for v in rows if not v[1]]
 if not pos or not neg:return None
 return sum((a>b)+.5*(a==b) for a in pos for b in neg)/(len(pos)*len(neg))

def read(path):
 b=Path(path).read_bytes(); assert digest(b)==PIN
 daily=defaultdict(lambda:{'sums':[0.]*14,'clocks':set(),'count':0,'dup':False})
 with Path(path).open(newline='',encoding='utf-8-sig') as f:
  reader=csv.reader(f);h=next(reader);assert len(h)==15 and h[0]=='Timestamp'
  n=0
  for row in reader:
   n+=1;date,clock=row[0].split();d,m,y=map(int,date.split('/'));ymd=f'{2000+y:04d}-{m:02d}-{d:02d}'
   v=daily[ymd];v['dup'] |= clock in v['clocks'];v['clocks'].add(clock);v['count']+=1
   for j,val in enumerate(row[1:]):v['sums'][j]+=float(val)
 assert n==280512
 calendars=defaultdict(dict)
 for day,r in daily.items():calendars[day[:7]][day]=r
 months={}
 for ym,days in calendars.items():
  year,month=map(int,ym.split('-'))
  expected=calendar.monthrange(year,month)[1]
  if len(days)==expected and all(x['count']==96 and len(x['clocks'])==96 and not x['dup'] for x in days.values()):
   months[ym]=[days[z]['sums'] for z in sorted(days)]
 assert len(months)==79 and len(calendars)==97
 return months

def shortlist(arr):
 top=max(arr);return tuple(i for i,x in enumerate(arr) if x>=.95*top-1e-10)
def score_and_labels(m):
 r=[]
 for ym,month in sorted(m.items()):
  nd=len(month)
  full=[sum(day[j] for day in month) for j in range(14)]
  truth=shortlist(full)
  for start in range(nd-2):
   retained=[sum(month[d][j] for d in range(nd) if not(start<=d<start+3)) for j in range(14)]
   pred=shortlist(retained)
   sc=-min(abs((p/max(retained))-.95) for p in retained)
   r.append((ym,sc,pred!=truth,100*3/nd))
 return r

def run(path):
 rows=score_and_labels(read(path))
 assert len(rows)==2237 and sum(x[2] for x in rows)==430
 chron=sorted({x[0] for x in rows}); tr=set(chron[:55]); te=set(chron[55:])
 dev=[x for x in rows if x[0] in tr];hold=[x for x in rows if x[0] in te]
 t=pctl([x[1] for x in dev],.75)
 pred=[(s>=t,y) for _,s,y,_ in hold]
 tp=sum(p and y for p,y in pred);fp=sum(p and not y for p,y in pred)
 fn=sum(not p and y for p,y in pred);tn=sum(not p and not y for p,y in pred)
 scores=[(s,y) for _,s,y,_ in hold]
 bymonth=[]
 for ym in sorted(te):
  rr=[(s,y) for m,s,y,_ in hold if m==ym]
  a=calc_auc(rr)
  if a is not None:bymonth.append(a)
 a=calc_auc(scores); med=statistics.median(bymonth)
 assert (len(dev),len(hold),tp,fp,fn,tn)==(1557,680,106,100,61,413),(len(dev),len(hold),tp,fp,fn,tn)
 assert abs(t-(-0.001077879123675074))<2e-11
 assert abs(a-0.7770890966604802)<2e-10
 assert abs(med-0.6525241675617615)<2e-10
 v={'R43_INDEPENDENT_PASS':True,'raw_source_git_blob':PIN,'n_months':79,
  'train_earliest_months':55,'test_latest_months':24,'test_windows':len(hold),
  'test_changed':sum(y for s,y in scores),'tp':tp,'fp':fp,'fn':fn,'tn':tn,
  'threshold':t,'auc':a,'median_month_auc':med,'method':'pure Python original row reader + retained direct summation'}
 print('R43_INDEPENDENT_PASS',json.dumps(v,sort_keys=True),flush=True)
 return v
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',default='R43_INDEPENDENT_DERIVED_ONLY');x=p.parse_args()
 a=run(x.source);d=Path(x.out);d.mkdir(parents=True,exist_ok=True);(d/'R43_INDEPENDENT_QA.json').write_text(json.dumps(a,indent=2))
