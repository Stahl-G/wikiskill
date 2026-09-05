"""Export only allowlisted train/val metadata from the originating experiments.

Explicit --source is a local experiment checkout. No test payloads, questions,
gold answers, generated answers, prompts, credentials or raw traces are copied.
"""
import argparse
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json,re

DOMAINS={'officeqa':24,'officeqa-retrieval':24,'livemath':18,'spreadsheet':40,'sealqa':10,'alfworld':18}
ARMS=['sol','55','terra','luna']
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.exists():raise SystemExit('Use a new snapshot directory; never overwrite an exported snapshot')
args.output.mkdir(parents=True)
inventory=[]
def read(path):
 for _ in range(3):
  a=path.stat();raw=path.read_bytes();b=path.stat()
  if (a.st_size,a.st_mtime_ns)==(b.st_size,b.st_mtime_ns):break
 else:raise RuntimeError('Source changed during snapshot')
 inventory.append({'source':str(path.relative_to(args.source)),'sha256':sha256(raw).hexdigest(),'bytes':len(raw)})
 return raw
def clean_id(uid):
 return str(uid).split('/json_2.1.1/')[-1] if '/json_2.1.1/' in str(uid) else str(uid)
def rows(path):
 if not path.exists():return []
 raw=[json.loads(s) for s in read(path).decode().splitlines() if s.strip()]
 unique={x.get('uid',x.get('case_id')):x for x in raw}
 return [{'uid':clean_id(k),**{f:v[f] for f in ['score','model','reported_model','skill_sha256','fail_reason'] if f in v}} for k,v in unique.items()]
cells=[];hist=[];paired=[]
for d,n in DOMAINS.items():
 for a in ARMS:
  base=args.source/'private_planning'/d;loop=base/'loops'/a
  p=loop/'val-s0.jsonl' if d=='officeqa' else base/'s0'/f'{a}-val-s0.jsonl';s0=rows(p)
  h=loop/'wiki/skill-impact.md'
  entries=[json.loads(s) for s in re.findall(r'```json\s*(.*?)```',read(h).decode(),re.S)] if h.exists() else []
  for e in entries:
   hist.append({'domain':d,'arm':a,**{k:e.get(k) for k in ['iteration','recorded_at','gate_verdict','accepted','skill_sha256','incumbent_descriptive','candidate_descriptive']}})
  accepted=[e for e in entries if e.get('accepted') and e.get('gate_verdict')=='ACCEPT']
  latest={e['iteration']:e for e in entries}
  rb=loop/'r_best.json';rb=json.loads(read(rb)) if rb.exists() else {}
  baseline=sum(x['score'] for x in s0)/n if len(s0)==n and all(x['score'] in (0,1) and x.get('fail_reason') not in {'exec_failed','exec_raised','score_failed','model_identity'} for x in s0) else None
  status='complete_k4' if all(i in latest and latest[i]['gate_verdict'] in ['ACCEPT','REJECT','NOT_GATED'] for i in range(1,5)) else 'early_stop_val_ceiling' if d=='alfworld' and baseline==1 else 'evolution_pending' if baseline is not None else 'not_run'
  cell={'domain':d,'arm':a,'val_n':n,'baseline':baseline,'retained':rb.get('r_best',baseline),'updated_at':rb.get('updated_at'),'status':status,'accepted_iteration':accepted[-1]['iteration'] if accepted else None,'exploratory':d=='officeqa-retrieval','skill':None}
  cand=s0
  if accepted:
   e=accepted[-1];it=e['iteration'];sk=loop/f'wiki/SKILL-it{it}.md';raw=read(sk)
   if re.search(rb'/Users/|/home/|sk-[A-Za-z0-9]{16}',raw):raise ValueError('Skill requires a manual privacy review')
   if sha256(raw).hexdigest()!=e['skill_sha256']:raise ValueError('Skill/gate mismatch')
   dest=args.output/f'skills/{d}/{a}.md';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
   cell['skill']=str(dest.relative_to(args.output));cell['skill_sha256']=sha256(raw).hexdigest()
   cand=rows(loop/f'it{it}/val-candidate.jsonl')
   if len(cand)!=n or any(x.get('skill_sha256')!=cell['skill_sha256'] for x in cand):raise ValueError('Candidate injection metadata mismatch')
   if abs(sum(x['score'] for x in cand)/n-cell['retained'])>1e-10:raise ValueError('Candidate score/r_best mismatch')
  indexed={x['uid']:x for x in cand}
  if baseline is not None:
   for x in s0:
    y=indexed[x['uid']]
    paired.append({'domain':d,'arm':a,'uid':x['uid'],'s0':x['score'],'retained_val':y['score'],'reported_model':y.get('reported_model')})
  cells.append(cell)
snapshot={'captured_at':datetime.now(timezone.utc).isoformat(),'scope':'historical validation outcomes; held-out generalization evaluation in progress, results pending','source_runtime':'Codex','independent_evolutions_per_cell':1,'scores_from_pre_extraction_harness':True,'cells':cells,'pairs':paired,'gate_events':hist,'source_inventory':inventory,'notes':['No test scores are included.','Missing model-echo metadata is null, not verified.','Gate events include historical infrastructure attempts and superseded outcomes.','Historical LiveMath scores are from v1 with the upstream meta-option artifact.','No raw model transcripts or restricted dataset contents are redistributed.']}
target=args.output/'snapshot.json';target.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
(args.output/'snapshot.sha256').write_text(sha256(target.read_bytes()).hexdigest()+'\n')
print(json.dumps({'output':str(args.output),'cells':len(cells),'accept_events':sum(e['accepted'] is True for e in hist),'captured_at':snapshot['captured_at']}))
