"""Render the bundled descriptive validation snapshot; no inference calls."""
from pathlib import Path
import argparse,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from wikiskill.settings import RESOURCES
from wikiskill.results import verify

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('assets/validation-results.png'));a=p.parse_args()
verify()
data=json.loads((RESOURCES/'research/snapshot.json').read_text())
domains=['officeqa','officeqa-retrieval','spreadsheet','livemath','sealqa','alfworld'];arms=['sol','55','terra','luna']
labels=['OfficeQA / staged','OfficeQA / retrieval','SpreadsheetBench','LiveMath (historical v1)','SealQA','ALFWorld (seen val)']
fig,ax=plt.subplots(figsize=(13,8.3));fig.patch.set_facecolor('#f7f9fb');ax.set_facecolor('#f7f9fb')
ax.set_xlim(-1.6,4);ax.set_ylim(6.5,-.9);ax.axis('off')
fig.suptitle('WikiSkill: recorded validation outcomes',fontsize=22,x=.06,ha='left',y=.98)
fig.text(.06,.916,'Baseline → retained score  |  2026-09-05 09:05 UTC  |  Held-out results pending',fontsize=12,color='#526779')
for j,s in enumerate(['Sol','GPT-5.5','Terra','Luna']):ax.text(j+.5,-.3,s,ha='center',fontsize=14,weight='bold')
for i,d in enumerate(domains):
 ax.text(-.10,i+.43,labels[i],ha='right',va='center',fontsize=11)
 for j,arm in enumerate(arms):
  c=next(x for x in data['cells'] if x['domain']==d and x['arm']==arm);b=c['baseline'];s=c['retained'];pending=c['status']=='evolution_pending'
  color='#e5eaf0' if b is None else '#d6eee5' if s>b else '#fff0d5' if pending else '#ffffff'
  ax.add_patch(Rectangle((j+.025,i+.015),.95,.87,color=color))
  if b is None:ax.text(j+.5,i+.4,'not run',ha='center',va='center',color='#8794a0');continue
  ax.text(j+.5,i+.23,f'{b*100:.1f} → {s*100:.1f}%',ha='center',va='center',fontsize=13)
  ax.text(j+.5,i+.48,f'N={c["val_n"]}  ·  Δ {(s-b)*100:+.1f} pp',ha='center',fontsize=10,color='#36614f')
  ax.text(j+.5,i+.71,'in progress' if pending else 'val ceiling' if c['status']=='early_stop_val_ceiling' else 'evolution complete',ha='center',fontsize=9,color='#586776')
fig.text(.06,.038,'Adaptively selected validation scores, not independent test estimates. Green does not denote statistical significance.',fontsize=10,color='#526779')
a.out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.out,dpi=150,bbox_inches='tight');print(a.out)
