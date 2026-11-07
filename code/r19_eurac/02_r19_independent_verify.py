from pathlib import Path
import pandas as pd, numpy as np, json, sys, itertools
RAW=Path(sys.argv[1]); OUT=Path(sys.argv[2]); P=Path(sys.argv[3]); SYSTEMS=['Trina','Sunpower','Sanyo','Wurth'];LABEL={'Trina':'Poly-Si','Sunpower':'Mono-Si','Sanyo':'HJT','Wurth':'CIGS'};STC={'Trina':2070.,'Sunpower':1200.,'Sanyo':3870.,'Wurth':1050.};C=.95
source={}
for s in SYSTEMS:
    df=pd.read_csv(RAW/f'EURAC/{s}/{s}.csv',sep=';',usecols=['Fecha','Pmpp (W)','Front GPOA (W/m²)']);df['t']=pd.to_datetime(df['Fecha'],utc=True);df['p']=pd.to_numeric(df['Pmpp (W)'],errors='coerce');df['g']=pd.to_numeric(df['Front GPOA (W/m²)'],errors='coerce');source[s]=df.set_index('t')[['p','g']]
idx=source[SYSTEMS[0]].index;assert all(source[s].index.equals(idx) for s in SYSTEMS);D=[]
for date in sorted(set(idx.date)):
    inds=[i for i,t in enumerate(idx) if t.date()==date];ps=np.column_stack([source[s].iloc[inds].p.to_numpy() for s in SYSTEMS]);g=source['Trina'].iloc[inds].g.to_numpy();mask=np.all(np.isfinite(ps),axis=1);gp=np.maximum(np.nan_to_num(g,nan=0),0);den=gp.sum();cov=gp[mask].sum()/den if den>0 else np.nan;y=(np.nansum(ps[mask,:],axis=0)*.25)/np.array([STC[s] for s in SYSTEMS]);D.append((pd.Timestamp(date),cov,*y))
d=pd.DataFrame(D,columns=['date','coverage',*SYSTEMS]);d['month']=d.date.dt.to_period('M').astype(str);d['admitted']=d.coverage>=.95
R=pd.read_csv(P/'R19_PRIMARY_DELETION_RADIUS.csv');W=pd.read_csv(P/'R19_PRIMARY_MINIMAL_WITNESSES.csv')
def sl(v):
    m=max(v);return tuple(SYSTEMS[i] for i,x in enumerate(v) if x+1e-12>=C*m)
checks=[]
for _,r in R.iterrows():
    x=d[(d.month==r.month)&d.admitted].sort_values('date');S=x[SYSTEMS].sum().to_numpy();checks.append(sl(S)==tuple(s for s in SYSTEMS if LABEL[s] in r.baseline_list.split('|')))
low={}
for _,r in R.iterrows():
    x=d[(d.month==r.month)&d.admitted].sort_values('date').reset_index(drop=True);X=x[SYSTEMS].to_numpy();S=X.sum(0);base=sl(S);found=None
    for k in range(1,min(4,len(x)-10)+1):
        for cc in itertools.combinations(range(len(x)),k):
            if sl(S-X[list(cc)].sum(0))!=base:found=k;break
        if found:break
    low[r.month]=found
wit_ok=[]
for _,w in W.iterrows():
    x=d[(d.month==w.month)&d.admitted].sort_values('date').reset_index(drop=True);S=x[SYSTEMS].sum().to_numpy();base=sl(S);dates=set(str(w.deleted_dates).split('|'));mask=x.date.dt.strftime('%Y-%m-%d').isin(dates);new=sl(S-x.loc[mask,SYSTEMS].sum().to_numpy());wit_ok.append((len(dates)==int(w.k)) and (new!=base))
qa={'independent_baseline_lists_all_match':all(checks),'low_k_exact_search':low,'all_primary_finite_witnesses_change_list':all(wit_ok),'witness_count':len(wit_ok),'expected_july_min1':low.get('2015-07')==1,'expected_november_min4':low.get('2015-11')==4,'note':'August k=16 optimality remains certified by primary generalized MILP/sorting solver; independent verifier confirms its witness but does not exhaustively enumerate k<16.'}
(OUT/'R19_INDEPENDENT_QA.json').write_text(json.dumps(qa,indent=2));print(json.dumps(qa,indent=2))
