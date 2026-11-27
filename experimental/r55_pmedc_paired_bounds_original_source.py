#!/usr/bin/env python3
"""Research-only post hoc decision-certificate feasibility (NO manuscript changes).

Source: original MORE-EU 14-array, 15-column Array Power.csv, hash locked.
Same 79 eligible complete months as R55-EP4: 55 development, 24 later test.
3 whole-day synchronized artificial gaps, q=5%; no imputation or invented data.
This retrospective test does not validate hard physical future energy bounds.
"""
import argparse, calendar, csv, hashlib, io, json, math
from pathlib import Path
from collections import Counter, defaultdict

BLOB = '5611277efdd581bb839ec380239846a43ebe0ba7'
J = 14
Q = .05
C = 1-Q
GAP = 3
EPS = 1e-10

def read_months(source):
    raw=Path(source).read_bytes()
    got=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    assert got==BLOB, ('original source lock failed',got)
    reader=csv.reader(io.StringIO(raw.decode('utf-8-sig')))
    head=next(reader)
    assert len(head)==15 and head[0]=='Timestamp',head
    days={}
    count=0
    for row in reader:
        count+=1
        assert len(row)==15, ('bad row',count)
        daytxt,clock=row[0].split()
        d,m,y=map(int,daytxt.split('/'))
        day=f'{2000+y:04d}-{m:02d}-{d:02d}'
        rec=days.setdefault(day,{'clocks':set(),'sums':[0.]*J,'n':0,'dupe':False})
        if clock in rec['clocks']:rec['dupe']=True
        rec['clocks'].add(clock)
        rec['n']+=1
        for j,field in enumerate(row[1:]):
            val=float(field)
            assert math.isfinite(val), (count,j)
            rec['sums'][j]+=val
    assert count==280512,count
    bymonth=defaultdict(list)
    for d,r in days.items():bymonth[d[:7]].append((d,r))
    months=[]
    for m,rows in sorted(bymonth.items()):
        y,mm=map(int,m.split('-'))
        nd=calendar.monthrange(y,mm)[1]
        if len(rows)!=nd:continue
        if any(r['n']!=96 or len(r['clocks'])!=96 or r['dupe'] for _,r in rows):continue
        months.append({'month':m,'days':[r['sums'] for _,r in sorted(rows)]})
    assert len(months)==79,len(months)
    return months

def block_vectors(month):
    d=month['days']
    for i in range(len(d)-GAP+1):
        missing=[sum(d[k][j] for k in range(i,i+GAP)) for j in range(J)]
        yield i+1,missing

def make_bounds(months):
    v=[missing for month in months for _,missing in block_vectors(month)]
    assert len(v)==1557,len(v)
    lo=[min(x[j] for x in v) for j in range(J)]
    hi=[max(x[j] for x in v) for j in range(J)]
    pairlo=[[min(x[j]-C*x[k] for x in v) for k in range(J)] for j in range(J)]
    pairhi=[[max(x[j]-C*x[k] for x in v) for k in range(J)] for j in range(J)]
    for j in range(J):
        for k in range(J):
            assert pairlo[j][k]>=lo[j]-C*hi[k]-EPS,('lower bound dominance',j,k)
            assert pairhi[j][k]<=hi[j]-C*lo[k]+EPS,('upper bound dominance',j,k)
    return lo,hi,pairlo,pairhi

def classify(retained,lo,hi,pairlo,pairhi,mode):
    out=[]
    for j in range(J):
        margins=[]
        for k in range(J):
            if j==k:continue # Self-comparison automatic for nonnegative PV output and q>=0.
            obs=retained[j]-C*retained[k]
            if mode=='independent':low=lo[j]-C*hi[k];upper=hi[j]-C*lo[k]
            else:low=pairlo[j][k];upper=pairhi[j][k]
            margins.append((obs+low,obs+upper))
        if all(lower>=EPS for lower,upper in margins):out.append('I')
        elif any(upper < -EPS for lower,upper in margins):out.append('E')
        else:out.append('?')
    return out

def run(source,out):
    months=read_months(source)
    lo,hi,plo,phi=make_bounds(months[:55])
    totals=Counter()
    by_month=[]
    candidate_rows=[]
    for month in months[55:]:
        days=month['days']; num=len(days);full=[sum(row[j] for row in days) for j in range(J)]
        assert min(full)>=0
        reference=[x >= C*max(full)-EPS for x in full]
        month_counter=Counter()
        for i,hidden in block_vectors(month):
            # Separate available observation from hidden ground truth: classification receives only retained rows.
            retained=[sum(row[j] for d,row in enumerate(days) if not (i-1 <= d <= i+1)) for j in range(J)]
            assert all(abs(retained[j]+hidden[j]-full[j])<1e-6 for j in range(J))
            indep=classify(retained,lo,hi,plo,phi,'independent')
            paired=classify(retained,lo,hi,plo,phi,'paired')
            assert sum(x!='?' for x in paired)>=sum(x!='?' for x in indep), ('certificate dominance',month['month'],i)
            # Joint coverage requires EVERY related constraint to hold simultaneously.
            cover_ind=all(lo[j]-EPS<=hidden[j]<=hi[j]+EPS for j in range(J))
            cover_pair=all(plo[j][k]-EPS<=hidden[j]-C*hidden[k]<=phi[j][k]+EPS for j in range(J) for k in range(J))
            totals['test_windows']+=1;month_counter['test_windows']+=1
            totals['independent_joint_covered']+=int(cover_ind)
            totals['paired_joint_covered']+=int(cover_pair)
            totals['both_joint_covered']+=int(cover_ind and cover_pair)
            observed_subset={j for j,y in enumerate(retained) if y >= C*max(retained)-EPS}
            totals['changed_shortlist_windows']+=int(observed_subset!={j for j,b in enumerate(reference) if b})
            fullcert={}
            for mode,status in [('independent',indep),('paired',paired)]:
                cert=[j for j,x in enumerate(status) if x!='?']
                false=[j for j in cert if (status[j]=='I')!=reference[j]]
                totals[mode+'_inclusions']+=status.count('I')
                totals[mode+'_exclusions']+=status.count('E')
                totals[mode+'_unresolved']+=status.count('?')
                totals[mode+'_incorrect_certifications']+=len(false)
                totals[mode+'_correct_certifications']+=len(cert)-len(false)
                totals[mode+'_fully_certified_windows']+=int(len(cert)==J)
                totals[mode+'_incorrect_fully_certified']+=int(len(cert)==J and bool(false))
                totals[mode+'_any_certification']+=int(bool(cert))
                totals[mode+'_erroneous_window']+=int(bool(false))
                totals[mode+'_certifications_when_joint_uncovered']+=len(cert)*(not (cover_ind if mode=='independent' else cover_pair))
                fullcert[mode]=len(cert)
            totals['paired_strictly_more_certified_windows']+=int(fullcert['paired']>fullcert['independent'])
            month_counter['paired_certifications']+=fullcert['paired']
            for j in range(J):
                candidate_rows.append((month['month'],i,j+1,int(reference[j]),indep[j],paired[j],int(cover_ind),int(cover_pair)))
        by_month.append({'month':month['month'],**dict(month_counter)})
    assert totals['test_windows']==680,totals
    assert totals['changed_shortlist_windows']==167,totals
    assert sum(totals['paired_'+k] for k in ['inclusions','exclusions','unresolved'])==680*14
    assert sum(totals['independent_'+k] for k in ['inclusions','exclusions','unresolved'])==680*14
    assert totals['paired_inclusions']+totals['paired_exclusions']>=totals['independent_inclusions']+totals['independent_exclusions']
    result={
        'state':'RESEARCH_ONLY_POST_HOC_FEASIBILITY_NOT_MANUSCRIPT_RESULT',
        'source':'original MORE-EU fourteen-array archive',
        'git_blob_sha1':BLOB,'admitted_months':79,'development_months':55,'test_months':24,
        'development_3day_windows':1557,'test_3day_windows':680,'test_candidate_decisions':9520,
        'q':Q,'missing_days':GAP,
        'model':'finite historical min/max envelopes; not hard future physical bounds or confidence intervals',
        'methods':{'independent':'marginal 3-day min/max per array across development','paired':'3-day min/max of y_j-(1-q)y_k on same development blocks'},
        'counts':dict(totals),
        'candidate_coverage':{k:{'decided':totals[k+'_inclusions']+totals[k+'_exclusions'],
             'decided_share':(totals[k+'_inclusions']+totals[k+'_exclusions'])/9520,
             'error_rate_conditional_on_decisions':totals[k+'_incorrect_certifications']/max(1,totals[k+'_inclusions']+totals[k+'_exclusions']),
             'incorrect':totals[k+'_incorrect_certifications']} for k in ('independent','paired')},
        'limits':[
           'Test used historical records already analysed in the R55 project, not an independent new cohort',
           'Historical envelope bounds are not physical limits and do not certify unknown future gaps',
           'Candidate decisions within shared months are dependent',
           'No prospective outage accuracy, no financial utility, no independent sensor calibration',
           'Purely algebraic paired dominance is not a novelty claim'],
        'original_telemetry_redistributed':False}
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'R55_PMEDC_FEASIBILITY_RESEARCH_ONLY.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (out/'R55_PMEDC_CANDIDATE_CLASSIFICATIONS_DERIVED_ONLY.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.writer(f);writer.writerow(['month','start_day','array_id','complete_reference_in','independent_status','paired_status','independent_joint_bound_covered','paired_joint_bound_covered']);writer.writerows(candidate_rows)
    (out/'R55_PMEDC_MONTHLY_DERIVED_ONLY.json').write_text(json.dumps(by_month,indent=2),encoding='utf8')
    print('R55_PMEDC_ORIGINAL_SOURCE_GATE_PASS')
    print(json.dumps({'test_windows':680,'main_counts':dict(totals),'coverage':result['candidate_coverage']},sort_keys=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',default='R55_PMEDC_FEASIBILITY_OUTPUTS')
    x=p.parse_args();run(x.source,x.out)
