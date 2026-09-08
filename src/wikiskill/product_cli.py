"""CLI surface for the model-agnostic host-agent workflow."""
from pathlib import Path
import json

COMMANDS={'start','tasks','next','record','learn','propose','feedback','retry','export','capabilities'}


def register(sub):
    start=sub.add_parser('start',help='Start a host-agent improvement workspace; no model calls')
    start.add_argument('workspace',type=Path)
    for flag in ['tasks','skill','project']:start.add_argument('--'+flag,type=Path)
    start.add_argument('--from',dest='from_workspace',type=Path,help='Carry retained skill, Wiki and feedback into a new task set')
    start.add_argument('--rounds',type=int,default=1)
    start.add_argument('--direction',choices=['maximize','minimize'],default='maximize')
    start.add_argument('--min-improvement',type=float,default=0.)
    start.add_argument('--scorer',help='JSON command array; reads task/output JSON from stdin and returns score JSON')
    start.add_argument('--scorer-timeout',type=float,default=120)
    for name in ['tasks','next','record','learn','propose','feedback','retry','export']:
        p=sub.add_parser(name,help={'tasks':'Attach training and validation tasks before execution','next':'Get work requests for your current agent','record':'Record an actual task output and its score','learn':'Apply trace-backed Wiki pattern updates','propose':'Submit a candidate skill or no_action','feedback':'Add user feedback directly to the Wiki inbox','retry':'Explicitly retry a failed request after resolving it','export':'Export the retained skill and provenance'}[name])
        p.add_argument('workspace',type=Path)
        if name=='tasks':p.add_argument('--file',type=Path,required=True)
        if name=='next':p.add_argument('--count',type=int,default=1)
        if name in ('record','learn','propose','retry'):p.add_argument('--request',required=True)
        if name=='record':
            p.add_argument('--output',type=Path);p.add_argument('--trace',type=Path);p.add_argument('--score',type=float);p.add_argument('--feedback',default='')
            p.add_argument('--success',choices=['true','false']);p.add_argument('--model');p.add_argument('--effort');p.add_argument('--runtime');p.add_argument('--error')
        if name=='learn':p.add_argument('--file',type=Path,required=True)
        if name=='propose':
            g=p.add_mutually_exclusive_group(required=True);g.add_argument('--skill',type=Path);g.add_argument('--no-action',action='store_true');p.add_argument('--note',default='')
        if name=='feedback':
            g=p.add_mutually_exclusive_group(required=True);g.add_argument('--text');g.add_argument('--file',type=Path);p.add_argument('--source')
        if name=='export':p.add_argument('destination',type=Path)
    sub.add_parser('capabilities',help='List product and research capabilities without model calls')


def handle(args):
    from . import product as p
    c=args.command
    if c=='capabilities':return p.capabilities()
    if c=='start':return p.start(args.workspace,tasks=args.tasks,skill=args.skill,rounds=args.rounds,direction=args.direction,min_improvement=args.min_improvement,scorer=json.loads(args.scorer) if args.scorer else None,scorer_timeout=args.scorer_timeout,project=args.project,from_workspace=args.from_workspace)
    if c=='tasks':return p.set_tasks(args.workspace,args.file)
    if c=='next':return p.next_work(args.workspace,args.count)
    if c=='record':return p.record(args.workspace,args.request,output=args.output,score=args.score,feedback=args.feedback,success=None if args.success is None else args.success=='true',model=args.model,runtime=args.runtime,error=args.error,trace=args.trace,effort=args.effort)
    if c=='learn':return p.learn(args.workspace,args.request,args.file)
    if c=='propose':return p.propose(args.workspace,args.request,skill=args.skill,note=args.note,no_action=args.no_action)
    if c=='feedback':return p.feedback(args.workspace,args.text if args.text is not None else args.file.read_text(encoding='utf-8'),args.source)
    if c=='retry':return p.retry(args.workspace,args.request)
    if c=='export':return p.export(args.workspace,args.destination)
    raise ValueError('Unknown product command')
