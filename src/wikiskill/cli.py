"""Command-line entry point; model calls happen only in evolve."""
import argparse
import json
import shutil
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(prog='wikiskill',description='Compile experience into validated agent skills')
    parser.add_argument('--version',action='version',version='WikiSkill 0.1.0')
    sub=parser.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init',help='Initialize an empty experiment; no model calls')
    init.add_argument('workspace',type=Path)
    init.add_argument('--domain',required=True,choices=['officeqa','officeqa-retrieval','livemath','spreadsheet','sealqa','alfworld'])
    init.add_argument('--model',required=True)
    init.add_argument('--optimizer-model')
    init.add_argument('--effort',default='medium')
    init.add_argument('--optimizer-effort',default='medium')
    init.add_argument('--iterations',type=int,default=4)
    init.add_argument('--workers',type=int,default=4)
    init.add_argument('--timeout',type=int,default=1800)
    for name in ['data','csv','corpus','split-dir']:init.add_argument('--'+name,type=Path)
    for name in ['evolve','status']:
        cmd=sub.add_parser(name,help='Run/resume train-val evolution' if name=='evolve' else 'Read experiment state')
        cmd.add_argument('workspace',type=Path)
    demo=sub.add_parser('demo',help='Deterministic offline demonstration; no model calls')
    demo.add_argument('workspace',type=Path)
    sub.add_parser('doctor',help='Check runtime availability without model calls')
    report=sub.add_parser('results',help='Verify and summarize the bundled research snapshot')
    report.add_argument('--snapshot',type=Path)
    args=parser.parse_args(argv)
    from . import engine
    try:
        if args.command=='doctor':
            print(json.dumps({'codex':shutil.which('codex'),'note':'CLI discovery only; auth and model access are not tested.'},indent=2));return 0
        if args.command=='results':
            from .results import verify
            print(json.dumps(verify(args.snapshot),indent=2));return 0
        if args.command=='init':
            config={k:str(v.resolve()) if isinstance(v,Path) else v for k,v in vars(args).items() if k not in {'command','workspace'}}
            config['optimizer_model']=args.optimizer_model or args.model
            if args.domain.startswith('officeqa') and (not args.csv or not args.corpus):parser.error('OfficeQA requires --csv and --corpus')
            if not args.domain.startswith('officeqa') and not args.data:parser.error('This domain requires --data')
            result=engine.initialize(args.workspace,config)
        elif args.command=='demo':
            engine.initialize(args.workspace,{'domain':'demo','model':'offline-demo','optimizer_model':'offline-demo',
                'effort':'none','optimizer_effort':'none','iterations':3,'workers':2,'timeout':10})
            result=engine.evolve(args.workspace)
        elif args.command=='status':result=engine.state(args.workspace.resolve())
        else:result=engine.evolve(args.workspace)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,RuntimeError,OSError,KeyError) as exc:
        parser.exit(2,f'WikiSkill: {exc}\n')


if __name__=='__main__':raise SystemExit(main())
