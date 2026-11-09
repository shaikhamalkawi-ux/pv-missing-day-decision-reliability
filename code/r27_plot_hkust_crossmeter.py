#!/usr/bin/env python3
"""R27 observed-data HKUST cross-meter scatter from R26L frozen derived file.

Figure represents 93 complete Library source-days only, no imputation. No raw
PV, calibration certificates, confidence intervals or pooled statistics.
"""
from pathlib import Path
import csv,statistics,math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

data=Path("r27_evidence/R26L/R26L_MATCHED_SOURCE_DAY_AUDIT.csv")
out=Path("figures/R27_HKUST_LIBRARY_SITE_VS_INVERTER.png")
with data.open(newline="",encoding="utf8") as f: rows=list(csv.DictReader(f))
library=[r for r in rows if r["group"]=="Library" and r["source_cohort"]=="1" and r["crossmeter_admitted"]=="1"]
assert len(library)==93,len(library)
months=sorted({r["date"][:7] for r in library})
assert months==["2022-07","2023-05","2023-07"],months
errors=[float(r["pct_abs_diff_station_power_vs_inverters"]) for r in library]
assert abs(statistics.median(errors)-0.42757788815049586)<1e-9
p95=sorted(errors)
x=(len(p95)-1)*.95
q95=p95[int(x)]*(1-(x%1))+p95[min(int(x)+1,len(p95)-1)]*(x%1)
assert abs(q95-0.9935278571786557)<1e-9
fig,ax=plt.subplots(figsize=(6.4,5.2))
markers=["o","s","^"]
for month,marker in zip(months,markers):
    src=[r for r in library if r["date"].startswith(month)]
    xx=[float(r["station_power_integral_rect_kwh"]) for r in src]
    yy=[float(r["sum_inverter_power_5min_integral_kwh"]) for r in src]
    ax.scatter(xx,yy,s=25,marker=marker,alpha=0.72,label=month)
allvals=[float(r[k]) for r in library for k in ("station_power_integral_rect_kwh","sum_inverter_power_5min_integral_kwh")]
low=min(allvals);high=max(allvals);pad=(high-low)*.045
ax.plot([low-pad,high+pad],[low-pad,high+pad],linestyle="--",linewidth=1.2,alpha=.75,label="1:1 reference")
ax.set_xlim(low-pad,high+pad);ax.set_ylim(low-pad,high+pad)
ax.set_xlabel("Energy from site power, 15-min integration (kWh)")
ax.set_ylabel("Sum of inverter energy, 5-min integration (kWh)")
ax.set_aspect("equal",adjustable="box")
ax.grid(True,linestyle=":",linewidth=.5,alpha=.5)
ax.legend(fontsize=8,loc="upper left")
ax.set_title("HKUST Library: 93 matched source-days",fontsize=11)
ax.text(.98,.03,"Median |difference| = 0.428%   P95 = 0.994%",
        transform=ax.transAxes,ha="right",va="bottom",fontsize=8,
        bbox=dict(boxstyle="round,pad=.25",fc="white",ec=".7",alpha=.8))
fig.tight_layout()
out.parent.mkdir(exist_ok=True,parents=True)
fig.savefig(out,dpi=180,bbox_inches="tight")
plt.close(fig)
print(f"R27_FIGURE_PASS: {out}, n={len(library)}, months={months}, median={statistics.median(errors):.9f}, p95={q95:.9f}")
