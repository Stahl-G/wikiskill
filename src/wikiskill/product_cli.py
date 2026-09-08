"""CLI surface for the model-agnostic host-agent workflow."""
from pathlib import Path
import json

COMMANDS={'start','tasks','next','record','learn','propose','feedback','retry','export','capabilities','scorer','preflight','report','install','restore','agents','dispatch','bind-agent','collect','fail'}


def register(sub):
    start=sub.add_parser('start',help='Start a host-agent improvement workspace; no model calls')
    start.add_argument('workspace',type=Path)
    for flag in ['tasks','skill','project']:start.add_argument('--'+flag,type=Path)
    start.add_argument('--from',dest='from_workspace',type=Path,help='Carry retained skill, Wiki and feedback into a new task set')
    start.add_argument('--agent-runtime',choices=['codex','claude-code'],help='Require fresh native subagent submissions')
    start.add_argument('--rounds',type=int,default=1)
    start.add_argument('--direction',choices=['maximize','minimize'],default='maximize')
    start.add_argument('--min-improvement',type=float,default=0.)
    start.add_argument('--scorer',help='JSON command array; reads task/output JSON from stdin and returns score JSON')
    start.add_argument('--trust-scorer',action='store_true',help='Explicitly authorize this locally configured scorer; do not use for unreviewed imported workspaces')
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
    agents=sub.add_parser('agents',help='Install native host roles and the coordinating entry skill')
    agent_actions=agents.add_subparsers(dest='agents_action',required=True)
    agent_install=agent_actions.add_parser('install')
    agent_install.add_argument('--runtime',choices=['codex','claude-code'],required=True)
    agent_install.add_argument('--project',type=Path,required=True)
    dispatch=sub.add_parser('dispatch',help='Prepare minimal native subagent handoffs; no model calls')
    dispatch.add_argument('workspace',type=Path)
    dispatch.add_argument('--runtime',choices=['codex','claude-code'],required=True)
    dispatch.add_argument('--count',type=int,default=1)
    bind=sub.add_parser('bind-agent',help='Record the actual host-returned fresh subagent ID')
    bind.add_argument('workspace',type=Path);bind.add_argument('--request',required=True)
    bind.add_argument('--agent-id',required=True);bind.add_argument('--runtime',choices=['codex','claude-code'],required=True)
    bind.add_argument('--context',choices=['fresh'],required=True)
    collect=sub.add_parser('collect',help='Submit the bound subagent output through normal scoring/learning/gating')
    collect.add_argument('workspace',type=Path);collect.add_argument('--request',required=True)
    collect.add_argument('--score',type=float);collect.add_argument('--feedback',default='')
    collect.add_argument('--success',choices=['true','false'])
    fail=sub.add_parser('fail',help='Preserve a native delegation or role failure for explicit recovery')
    fail.add_argument('workspace',type=Path);fail.add_argument('--request',required=True);fail.add_argument('--error',required=True)
    sc=sub.add_parser('scorer',help='Inspect or locally authorize an external scorer')
    sp=sc.add_subparsers(dest='scorer_action',required=True)
    for action in ['inspect','trust']:
        q=sp.add_parser(action);q.add_argument('workspace',type=Path)
        if action=='trust':q.add_argument('--fingerprint',required=True)
    ins=sub.add_parser('install',help='Install a completed retained SKILL.md to an explicitly selected directory')
    ins.add_argument('workspace',type=Path)
    ins.add_argument('destination',type=Path)
    ins.add_argument('--replace',action='store_true',help='Back up and replace an existing SKILL.md')
    restore=sub.add_parser('restore',help='Restore a local skill backup without discarding later edits')
    restore.add_argument('destination',type=Path)
    restore.add_argument('--backup',required=True)
    pf=sub.add_parser('preflight',help='Inspect task files and scorer readiness without executing them')
    pf.add_argument('workspace',type=Path)
    rp=sub.add_parser('report',help='Read a result report derived from the workspace journal')
    rp.add_argument('workspace',type=Path)
    rp.add_argument('--format',choices=['markdown','json'],default='markdown')
    sub.add_parser('capabilities',help='List product and research capabilities without model calls')


def handle(args):
    from . import product as p
    c=args.command
    if c in ('agents','dispatch','bind-agent','collect','fail'):
        from . import native_agents as n
        if c=='agents':return n.install(args.project,args.runtime)
        if c=='dispatch':return n.dispatch(args.workspace,args.runtime,args.count)
        if c=='bind-agent':return n.bind(args.workspace,args.request,args.agent_id,args.runtime,args.context)
        if c=='collect':return n.collect(args.workspace,args.request,score=args.score,feedback=args.feedback,success=None if args.success is None else args.success=='true')
        return n.fail(args.workspace,args.request,args.error)
    if c in ('install','restore'):
        from . import product_install
        return product_install.install(args.workspace,args.destination,replace=args.replace) if c=='install' else product_install.restore(args.destination,args.backup)
    if c in ('preflight','report'):
        from . import product_views as views
        return views.preflight(args.workspace) if c=='preflight' else views.report(args.workspace)
    if c=='capabilities':return p.capabilities()
    if c=='scorer':return p.scorer_inspect(args.workspace) if args.scorer_action=='inspect' else p.scorer_trust(args.workspace,args.fingerprint)
    if c=='start':return p.start(args.workspace,tasks=args.tasks,skill=args.skill,rounds=args.rounds,direction=args.direction,min_improvement=args.min_improvement,scorer=json.loads(args.scorer) if args.scorer else None,scorer_timeout=args.scorer_timeout,project=args.project,from_workspace=args.from_workspace,trust_scorer=args.trust_scorer,agent_runtime=args.agent_runtime)
    if c=='tasks':return p.set_tasks(args.workspace,args.file)
    if c=='next':return p.next_work(args.workspace,args.count)
    if c=='record':return p.record(args.workspace,args.request,output=args.output,score=args.score,feedback=args.feedback,success=None if args.success is None else args.success=='true',model=args.model,runtime=args.runtime,error=args.error,trace=args.trace,effort=args.effort)
    if c=='learn':return p.learn(args.workspace,args.request,args.file)
    if c=='propose':return p.propose(args.workspace,args.request,skill=args.skill,note=args.note,no_action=args.no_action)
    if c=='feedback':return p.feedback(args.workspace,args.text if args.text is not None else args.file.read_text(encoding='utf-8'),args.source)
    if c=='retry':return p.retry(args.workspace,args.request)
    if c=='export':return p.export(args.workspace,args.destination)
    raise ValueError('Unknown product command')
