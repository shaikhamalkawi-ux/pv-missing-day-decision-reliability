from pathlib import Path
import pandas as pd, numpy as np, hashlib, json, math, itertools, sys
from scipy.optimize import milp, LinearConstraint, Bounds
RAW=Path(sys.argv[1]); OUT=Path(sys.argv[2]); OUT.mkdir(parents=True,exist_ok=True)
RAR=Path(sys.argv[3]) if len(sys.argv)>3 else None
ZENODO_MD5='2a943acd9f7c52702cdfdc33cd320a70'; ZENODO_DOI='10.5281/zenodo.18316996'
SYSTEMS=['Trina','Sunpower','Sanyo','Wurth']; LABEL={'Trina':'Poly-Si','Sunpower':'Mono-Si','Sanyo':'HJT','Wurth':'CIGS'}
Q=.05; C=1-Q; MIN_RETAIN=10; SUPPORT=.95; EPS=1e-10

def h(path,alg='sha256'):
    x=hashlib.new(alg)
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):x.update(b)
    return x.hexdigest()

def dec(s):return float(str(s).replace(',','.'))
meta=pd.read_csv(RAW/'EURAC/Electric_information_EURAC.csv',sep=';',dtype=str)
meta=meta.set_index('Name')
rows=[];stc={}
for s in SYSTEMS:
    r=meta.loc[s]; n=int(r['Total number of PV modules']); p=dec(r['PV MODULE Maximum Power STC(Pmax)']); stc[s]=n*p
    rows.append({'system':s,'technology':r['PV MODULE Technology'],'module_brand':r['PV MODULE Brand'],'module_reference':r['PV MODULE Reference'],'module_count':n,'module_stc_W':p,'system_stc_W_derived':stc[s],'latitude':r['Latitude (Decimal degrees)'],'longitude':r['longitude (Decimal degrees)'],'interval_min':r['Time Interval (min)'],'first_timestamp':r['First Timestamp (DD/MM/AAAA)'],'last_timestamp':r['Last Timestamp (DD/MM/AAAA)']})
r=meta.loc['First Solar']; rows.append({'system':'First Solar','technology':r['PV MODULE Technology'],'module_brand':r['PV MODULE Brand'],'module_reference':r['PV MODULE Reference'],'module_count':r['Total number of PV modules'],'module_stc_W':dec(r['PV MODULE Maximum Power STC(Pmax)']),'system_stc_W_derived':'EXCLUDED_METADATA_AMBIGUOUS','latitude':r['Latitude (Decimal degrees)'],'longitude':r['longitude (Decimal degrees)'],'interval_min':r['Time Interval (min)'],'first_timestamp':r['First Timestamp (DD/MM/AAAA)'],'last_timestamp':r['Last Timestamp (DD/MM/AAAA)']})
pd.DataFrame(rows).to_csv(OUT/'R19_SYSTEM_METADATA_AND_ADMISSION.csv',index=False)
src={'doi':ZENODO_DOI,'official_url':'https://zenodo.org/records/18316996','official_file':'EURAC.rar','official_md5':ZENODO_MD5}
if RAR:
    src.update({'local_md5':h(RAR,'md5'),'local_sha256':h(RAR,'sha256'),'md5_matches_official':h(RAR,'md5')==ZENODO_MD5,'local_bytes':RAR.stat().st_size})
(OUT/'R19_SOURCE_IDENTITY.json').write_text(json.dumps(src,indent=2))
j=None; stats=[]
for s in SYSTEMS:
    p=RAW/f'EURAC/{s}/{s}.csv'; df=pd.read_csv(p,sep=';',low_memory=False)
    df['ts']=pd.to_datetime(df['Fecha'],utc=True); df['Pmpp']=pd.to_numeric(df['Pmpp (W)'],errors='coerce'); df['Pac']=pd.to_numeric(df['Pac(W)'],errors='coerce'); df['GPOA']=pd.to_numeric(df['Front GPOA (W/m²)'],errors='coerce')
    stats.append({'system':s,'rows':len(df),'first_ts':str(df.ts.min()),'last_ts':str(df.ts.max()),'Pmpp_nonnull':int(df.Pmpp.notna().sum()),'Pac_nonnull':int(df.Pac.notna().sum()),'GPOA_nonnull':int(df.GPOA.notna().sum()),'csv_sha256':h(p)})
    x=df[['ts','Pmpp','Pac','GPOA']].set_index('ts').rename(columns={'Pmpp':f'{s}_Pmpp','Pac':f'{s}_Pac','GPOA':f'{s}_GPOA'})
    j=x if j is None else j.join(x,how='outer')
pd.DataFrame(stats).to_csv(OUT/'R19_SOURCE_FILE_STATS.csv',index=False)
for s in SYSTEMS[1:]:
    z=(j['Trina_GPOA']-j[f'{s}_GPOA']).abs().dropna()
    if len(z)==0 or z.max()!=0: raise AssertionError('GPOA mismatch '+s)
j['date']=pd.to_datetime(j.index.date)
def build_daily(endpoint):
    rec=[]
    for d,g in j.groupby('date'):
        gpoa=g['Trina_GPOA'].clip(lower=0); shared=np.logical_and.reduce([g[f'{s}_{endpoint}'].notna() for s in SYSTEMS])
        full=float((gpoa.fillna(0)*.25).sum()); com=float((gpoa.where(shared,0).fillna(0)*.25).sum()); coverage=com/full if full>0 else np.nan
        r={'date':d,'endpoint':endpoint,'gpoa_Wh_m2':full,'common_gpoa_Wh_m2':com,'irradiance_support_fraction':coverage,'shared_samples':int(shared.sum())}
        for s in SYSTEMS:
            e=float((g.loc[shared,f'{s}_{endpoint}']*.25).sum());r[f'{s}_energy_Wh_common']=e;r[f'{s}_specific_yield_h']=e/stc[s]
        rec.append(r)
    d=pd.DataFrame(rec);d['admitted']=d.irradiance_support_fraction.ge(SUPPORT)&d.irradiance_support_fraction.notna();d['month']=d.date.dt.to_period('M').astype(str);return d
pmp=build_daily('Pmpp'); pac=build_daily('Pac'); pmp.to_csv(OUT/'R19_DAILY_COMMON_SUPPORT_PRIVATE.csv',index=False)
m=pmp.groupby('month').agg(calendar_days=('date','count'),admitted_days=('admitted','sum'),min_support=('irradiance_support_fraction','min'),mean_support=('irradiance_support_fraction','mean')).reset_index();m['complete_admitted']=m.calendar_days.eq(m.admitted_days);m.to_csv(OUT/'R19_MONTH_SUPPORT.csv',index=False)
COMP=m.loc[m.complete_admitted,'month'].tolist()
def sl(S,q=Q):
    c=1-q;mx=float(np.max(S));return tuple(SYSTEMS[i] for i,x in enumerate(S) if x+1e-12>=c*mx)
def min_excl(X,S,t,maxdel,q=Q):
    c=1-q;best=None
    for u in range(len(SYSTEMS)):
        if u==t:continue
        margin=S[t]-c*S[u];a=X[:,t]-c*X[:,u];order=np.argsort(-a);cum=0;ch=[]
        for idx in order[:maxdel]:
            if a[idx]<=0:break
            cum+=a[idx];ch.append(int(idx))
            if cum>margin+EPS:
                z=(len(ch),ch.copy(),u,'exclude');best=z if best is None or z[0]<best[0] else best;break
    return best
def min_incl(X,S,t,maxdel,q=Q):
    c=1-q;A=np.vstack([X[:,t]-c*X[:,u] for u in range(len(SYSTEMS)) if u!=t]);ub=np.array([S[t]-c*S[u] for u in range(len(SYSTEMS)) if u!=t])
    cons=[LinearConstraint(A,-np.inf*np.ones(len(ub)),ub+1e-12),LinearConstraint(np.ones((1,len(X))),-np.inf,maxdel)]
    res=milp(c=np.ones(len(X)),integrality=np.ones(len(X)),bounds=Bounds(np.zeros(len(X)),np.ones(len(X))),constraints=cons,options={'time_limit':30})
    if not res.success:return None
    ch=np.flatnonzero(res.x>.5).tolist();S2=S-X[ch].sum(0) if ch else S.copy()
    if SYSTEMS[t] not in sl(S2,q):return None
    return (len(ch),ch,None,'include')
def threshold_margin(S,q=Q):
    c=1-q;mx=float(np.max(S));lead=int(np.argmax(S));ans=[]
    for i,x in enumerate(S):
        if i==lead:continue
        r=float(x/mx);e=(r-c)/(r+c) if r>=c else (c-r)/(c+r);ans.append((i,r,float(e),'included' if r>=c else 'excluded'))
    return min(ans,key=lambda z:z[2])
def analyze_months(daily, endpoint, support=SUPPORT, q=Q, complete_override=None):
    z=daily.copy();z['adm2']=z.irradiance_support_fraction.ge(support)&z.irradiance_support_fraction.notna();mm=z.groupby('month').agg(n=('date','count'),a=('adm2','sum')).reset_index();months=mm.loc[mm.n.eq(mm.a),'month'].tolist() if complete_override is None else complete_override
    R=[];W=[]
    for month in months:
        d=z[(z.month==month)&z.adm2].sort_values('date').reset_index(drop=True);X=np.column_stack([d[f'{s}_specific_yield_h'].to_numpy(float) for s in SYSTEMS]);S=X.sum(0);base=sl(S,q);n=len(X);maxdel=n-MIN_RETAIN;b={SYSTEMS.index(t) for t in base};cand=[]
        for t in range(len(SYSTEMS)):
            zz=min_excl(X,S,t,maxdel,q) if t in b else min_incl(X,S,t,maxdel,q)
            if zz:cand.append((zz[0],t,zz))
        best=min(cand,key=lambda x:x[0]) if cand else None;mi=threshold_margin(S,q)
        rr={'endpoint':endpoint,'support_gate':support,'q':q,'month':month,'days':n,'baseline_list':'|'.join(LABEL[s] for s in base),'closest_boundary_system':LABEL[SYSTEMS[mi[0]]],'closest_boundary_ratio_to_leader':mi[1],'symmetric_relative_yield_radius_to_boundary':mi[2],'closest_boundary_state':mi[3]}
        for i,s in enumerate(SYSTEMS):rr[f'{LABEL[s]}_full_yield_h']=float(S[i])
        if best:
            k,t,zz=best;ch=zz[1];S2=S-X[ch].sum(0);new=sl(S2,q);rr.update({'min_adversarial_deletions':k,'min_deletion_fraction':k/n,'retained_at_flip':n-k,'new_list':'|'.join(LABEL[s] for s in new)})
            W.append({'endpoint':endpoint,'support_gate':support,'q':q,'month':month,'k':k,'mechanism':zz[3],'target_system':LABEL[SYSTEMS[t]],'deleted_dates':'|'.join(d.iloc[ch].date.dt.strftime('%Y-%m-%d')),'baseline_list':'|'.join(LABEL[s] for s in base),'new_list':'|'.join(LABEL[s] for s in new)})
        else:rr.update({'min_adversarial_deletions':np.nan,'min_deletion_fraction':np.nan,'retained_at_flip':np.nan,'new_list':''})
        R.append(rr)
    return pd.DataFrame(R),pd.DataFrame(W)
R,W=analyze_months(pmp,'Pmpp');R.to_csv(OUT/'R19_PRIMARY_DELETION_RADIUS.csv',index=False);W.to_csv(OUT/'R19_PRIMARY_MINIMAL_WITNESSES.csv',index=False)
rng=np.random.default_rng(20261108);sens=[]
for month in COMP:
    d=pmp[(pmp.month==month)&pmp.admitted].sort_values('date').reset_index(drop=True);X=np.column_stack([d[f'{s}_specific_yield_h'].to_numpy(float) for s in SYSTEMS]);S=X.sum(0);base=sl(S);n=len(X)
    for k in [1,2,3,5,10]:
        if n-k<MIN_RETAIN:continue
        total=math.comb(n,k);ne=min(total,20000);chg=0;actual=0
        it=itertools.combinations(range(n),k) if total<=20000 else (rng.choice(n,k,replace=False) for _ in range(ne));mode='exact' if total<=20000 else 'mc'
        for cc in it:
            idx=np.array(cc,dtype=int);chg+=sl(S-X[idx].sum(0))!=base;actual+=1
        cchg=0;cn=0
        for start in range(n-k+1):
            idx=np.arange(start,start+k);cchg+=sl(S-X[idx].sum(0))!=base;cn+=1
        sens.append({'month':month,'k_deleted':k,'random_change_rate':chg/actual,'n_random_eval':actual,'random_mode':mode,'contiguous_change_rate':cchg/cn,'n_contiguous_eval':cn})
pd.DataFrame(sens).to_csv(OUT/'R19_RANDOM_BLOCK_SENSITIVITY.csv',index=False)
gate=[]
for support in [.90,.95,.98]:
    a,_=analyze_months(pmp,'Pmpp',support=support,q=Q)
    for _,r in a.iterrows():gate.append({'support_gate':support,'month':r.month,'baseline_list':r.baseline_list,'min_adversarial_deletions':r.min_adversarial_deletions})
pd.DataFrame(gate).to_csv(OUT/'R19_SUPPORT_GATE_SENSITIVITY.csv',index=False)
qs=[]
for q in [0,.025,.05,.075,.10]:
    a,_=analyze_months(pmp,'Pmpp',support=SUPPORT,q=q,complete_override=COMP)
    for _,r in a.iterrows():qs.append({'q':q,'month':r.month,'baseline_list':r.baseline_list,'min_adversarial_deletions':r.min_adversarial_deletions})
pd.DataFrame(qs).to_csv(OUT/'R19_Q_SENSITIVITY.csv',index=False)
A,AW=analyze_months(pac,'Pac',support=SUPPORT,q=Q,complete_override=COMP);A.to_csv(OUT/'R19_AC_ENDPOINT_SENSITIVITY.csv',index=False);AW.to_csv(OUT/'R19_AC_ENDPOINT_WITNESSES.csv',index=False)
finite=R.min_deletion_fraction.notna();one=(R.min_adversarial_deletions==1).sum()
sumry={'primary_endpoint':'DC Pmpp integrated on exact four-system common 15-minute timestamps','q':Q,'min_retained_days':MIN_RETAIN,'daily_irradiance_support_gate':SUPPORT,'source_days':365,'admitted_days':int(pmp.admitted.sum()),'complete_primary_months':len(R),'finite_deletion_radius_months':int(finite.sum()),'no_change_with_10_retained_months':int((~finite).sum()),'one_day_flip_months':int(one),'smallest_deletion_fraction':float(R.loc[finite,'min_deletion_fraction'].min()),'median_finite_deletion_fraction':float(R.loc[finite,'min_deletion_fraction'].median()),'first_solar_primary_status':'EXCLUDED: total module count / system STC not defensibly numeric in supplied metadata','gpoa_series_exactly_identical_across_four_system_files':True,'official_md5_match':bool(src.get('md5_matches_official',False))}
(OUT/'R19_SUMMARY.json').write_text(json.dumps(sumry,indent=2));print(json.dumps(sumry,indent=2))
