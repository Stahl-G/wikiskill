#!/usr/bin/env python3
"""Recompute final paired scores and UID-cluster repeated VAL; no model calls."""
from pathlib import Path
import argparse, hashlib, json, random, statistics
from check_research_update import analyze

ARMS=('no_skill','old_skill','new_skill','astra_skill')
def interval(values,seed):
    rng=random.Random(seed);v=sorted(statistics.mean(rng.choices(values,k=len(values))) for _ in range(10000))
    def q(p):
        x=9999*p;i=int(x);return v[i]+(v[min(i+1,9999)]-v[i])*(x-i)
    return [q(.025),q(.975)]

def check(root):
    root=Path(root);load=lambda n:json.loads((root/n).read_text())
    for name,digest in load('manifest.json')['files'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed artifact: '+name)
    summary=load('summary.json');out={}
    for name,study in summary['studies'].items():
        a=analyze(load(study['pairs_file']),study['bootstrap_seed'],study['bootstrap_samples'])
        a['p_bonferroni_four_domains']=min(1.,4*a['p_exact'])
        lo,hi=a['bootstrap_95_ci'];d=a['delta'];p=a['p_bonferroni_four_domains']
        a['verdict']='supported_improvement' if d>0 and lo>0 and p<.05 else 'supported_decrease' if d<0 and hi<0 and p<.05 else 'inconclusive'
        if a!=study['statistics']:raise ValueError('Paired statistics mismatch: '+name)
        out[name]=a
    m=summary['math'];rows=load('math-episodes.json');uids=m['uids'];keys={(r['repeat'],r['uid'],r['arm']):r for r in rows}
    expected={(rep,u,a) for rep in (1,2) for u in uids for a in ARMS}
    if len(uids)!=18 or len(set(uids))!=18 or len(rows)!=144 or set(keys)!=expected or any(r['score'] not in (0,1) or r['tool_calls']!=0 for r in rows):raise ValueError('Math membership/score/tool mismatch')
    s=m['statistics']
    for rep in (1,2):
        correct={a:sum(keys[(rep,u,a)]['score'] for u in uids) for a in ARMS}
        if correct!=s['per_repeat'][str(rep)]['correct']:raise ValueError('Repeat score mismatch')
        for arm in ARMS[1:]:
            diffs=[keys[(rep,u,arm)]['score']-keys[(rep,u,'no_skill')]['score'] for u in uids]
            if s['per_repeat'][str(rep)]['vs_no_skill'][arm]!={'delta':statistics.mean(diffs),'wins':diffs.count(1),'losses':diffs.count(-1)}:raise ValueError('Repeat contrast mismatch')
    baseline=[(keys[(1,u,'no_skill')]['score'],keys[(2,u,'no_skill')]['score']) for u in uids]
    b={'both_correct':sum(a==b==1 for a,b in baseline),'both_wrong':sum(a==b==0 for a,b in baseline),'wrong_to_correct':sum(a==0 and b==1 for a,b in baseline),'correct_to_wrong':sum(a==1 and b==0 for a,b in baseline),'flipped_questions':sum(a!=b for a,b in baseline),'accuracy_delta_repeat2_minus_repeat1':statistics.mean(b-a for a,b in baseline)}
    if b!=s['baseline_repeatability']:raise ValueError('Baseline repeatability differs')
    for arm in ARMS:
        group=[r for r in rows if r['arm']==arm];v=s['arms'][arm]
        for key,actual in [('mean_accuracy',statistics.mean(r['score'] for r in group)),('mean_seconds',statistics.mean(r['seconds'] for r in group)),('tool_calls',sum(r['tool_calls'] for r in group))]:
            if v[key]!=actual:raise ValueError('Math summary differs: '+key)
        if arm!='no_skill':
            diff=[statistics.mean(keys[(rep,u,arm)]['score']-keys[(rep,u,'no_skill')]['score'] for rep in (1,2)) for u in uids]
            if v['mean_delta_vs_no_skill']!=statistics.mean(diff) or v['uid_cluster_bootstrap_95_ci']!=interval(diff,m['analysis_seed']):raise ValueError('Cluster uncertainty differs')
    out['math']={'clusters':18,'episodes':144,'per_repeat':s['per_repeat'],'baseline_repeatability':b}
    skill=root/'spreadsheet-SKILL.md'
    if hashlib.sha256(skill.read_bytes()).hexdigest()!=summary['studies']['spreadsheet']['skill_sha256']:raise ValueError('Published skill differs')
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',nargs='?',type=Path,default=Path(__file__).resolve().parents[1]/'src/wikiskill/resources/research/final-20260907')
    print(json.dumps(check(p.parse_args().directory),indent=2))
