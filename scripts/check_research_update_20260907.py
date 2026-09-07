#!/usr/bin/env python3
"""Recompute September 7 paired tests and the six-cell exploratory screen."""
from pathlib import Path
import argparse
import json
import random
import statistics
from check_research_update import check,analyze


def quantile(values,q):
    values=sorted(values);x=(len(values)-1)*q;i=int(x)
    return values[i]+(values[min(i+1,len(values)-1)]-values[i])*(x-i)


def check_all(root):
    root=Path(root);completed=check(root)
    rows=json.loads((root/'effort-pairs.json').read_text());saved=json.loads((root/'effort-analysis.json').read_text())
    cells=[f'{effort}_{arm}' for effort in ('medium','high','max') for arm in ('s0','sk')]
    if len(rows)!=24 or len({r['uid'] for r in rows})!=24:raise ValueError('Invalid effort membership')
    for r in rows:
        if set(r)!={'uid',*cells} or any(r[c] not in (0,1) for c in cells):raise ValueError('Invalid effort row')
    conditions={c:{'correct':sum(r[c] for r in rows),'accuracy':statistics.mean(r[c] for r in rows)} for c in cells}
    if conditions!=saved['conditions']:raise ValueError('Condition score mismatch')
    vectors={e:[(r[f'{e}_sk']-r[f'{e}_s0'])-(r['medium_sk']-r['medium_s0']) for r in rows] for e in ('high','max')}
    for effort,values in vectors.items():
        rng=random.Random(2026090702);boot=[sum(rng.choices(values,k=24))/24 for _ in range(10000)]
        expected={'estimate':statistics.mean(values),'bootstrap_95_ci':[quantile(boot,.025),quantile(boot,.975)]}
        observed=saved['primary'] if effort=='max' else saved['high_interaction']
        if any(observed[k]!=v for k,v in expected.items()):raise ValueError('Effort interaction mismatch')
    contrasts=[(f'skill_at_{e}',f'{e}_s0',f'{e}_sk') for e in ('medium','high','max')]
    contrasts += [(f'{e}_minus_medium_without_skill','medium_s0',f'{e}_s0') for e in ('high','max')]
    ps=[]
    for name,a,b in contrasts:
        result=analyze([{'uid':r['uid'],'s0':r[a],'sk':r[b]} for r in rows],2026090702,10000)
        observed=next(v for v in saved['secondary'] if v['name']==name)
        mapped={'win':'wins','loss':'losses','delta':'delta','bootstrap_95_ci':'bootstrap_95_ci','p_exact':'p_exact','both_correct':'both_correct','both_wrong':'both_wrong'}
        if any(observed[k]!=result[v] for k,v in mapped.items()):raise ValueError('Secondary contrast mismatch: '+name)
        ps.append(observed)
    maximum=0.0
    for rank,item in enumerate(sorted(ps,key=lambda v:v['p_exact'])):
        maximum=max(maximum,min(1.0,(len(ps)-rank)*item['p_exact']))
        if item['p_holm']!=maximum:raise ValueError('Holm correction mismatch')
    return {'held_out':completed,'effort':{'n_tasks':24,'conditions':conditions,'primary':saved['primary'],'all_secondary_contrasts_verified':True}}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',nargs='?',type=Path,default=Path(__file__).resolve().parents[1]/'src/wikiskill/resources/research/update-20260907')
    print(json.dumps(check_all(p.parse_args().directory),indent=2))
