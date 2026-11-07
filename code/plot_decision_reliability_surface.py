#!/usr/bin/env python3
import argparse, csv
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
DATASETS = ["PROPRE.MA", "EURAC", "MORE-EU"]
def load(path):
    rows=list(csv.DictReader(open(path,encoding='utf-8')));out={}
    for r in rows:
        ds=r.get('dataset') or r.get('source');q=float(r['q']);L=int(float(r.get('gap_days',r.get('L',0))));frac=float(r.get('fragile_fraction',r.get('fragile_by_L_fraction',0)));out.setdefault(ds,{})[(q,L)]=frac
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--surface',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();data=load(a.surface);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    for ds in DATASETS:
        if ds not in data: continue
        qs=sorted({q for q,_ in data[ds]});Ls=sorted({L for _,L in data[ds]});z=np.array([[100*data[ds].get((q,L),np.nan) for L in Ls] for q in qs]);fig,ax=plt.subplots(figsize=(7.2,4.4));im=ax.imshow(z,aspect='auto',origin='lower');ax.set_xticks(range(len(Ls)),Ls);ax.set_yticks(range(len(qs)),[f'{100*q:g}%' for q in qs]);ax.set_xlabel('Maximum contiguous missing gap L (days)');ax.set_ylabel('Shortlist margin q');ax.set_title(f'{ds}: fragile admitted months (%)');fig.colorbar(im,ax=ax,label='Fragile months (%)')
        for i in range(z.shape[0]):
            for j in range(z.shape[1]):
                if np.isfinite(z[i,j]): ax.text(j,i,f'{z[i,j]:.1f}',ha='center',va='center',fontsize=8)
        fig.tight_layout();name_map={'PROPRE.MA':'R22_SURFACE_PROPREMA.png','EURAC':'R22_SURFACE_EURAC.png','MORE-EU':'R22_SURFACE_MORE_EU.png'};fig.savefig(out/name_map[ds],dpi=200);plt.close(fig)
if __name__=='__main__': main()
