"""Public feedback-first extension to the WikiSkill product journal.

Reuse product/native-agent requests for Maintainer and Proposer. The host supplies
real paired results; deterministic selection records the lightweight policy.
The original numeric task loop remains unchanged.
"""
from pathlib import Path
from . import product as p


def begin(root, *, feedback, skill=None, rounds=1, previous=None, runtime='codex'):
    root=Path(root).resolve()
    if (root/'config.json').exists():
        return work(root)
    p.start(root,skill=skill,rounds=rounds,from_workspace=previous,agent_runtime=runtime)
    for item in feedback:
        p.feedback(root,item['text'],source=item.get('source'))
    with p.locked(root):
        s=p._load(root)
        s=p._event(root,s,'feedback_mode',{})
        p._event(root,s,'phase',{'phase':'maintainer', **({'current_skill':None} if skill is None else {})})
    return work(root)


def work(root):
    root=Path(root).resolve();s=p._load(root)
    if not s.get('feedback_mode'):raise ValueError('Not a feedback study')
    return {'phase':s['phase'],'round':s['round'],'rounds':s['config']['rounds'],
            'candidate':s['candidate'],'current_skill':s['current_skill'],
            'patterns':s['patterns'],'history':s['history'],'feedback':s['feedback']}


def finish(root, *, pairs, reason='', evidence_file=None):
    root=Path(root).resolve()
    with p.locked(root):
        s=p._load(root)
        if s['phase']!='validation' or not s['candidate']:raise ValueError('No candidate awaiting comparison')
        candidate=s['candidate'];no_action=candidate['no_action']
        if not no_action:
            if not pairs or len({x['case_id'] for x in pairs})!=len(pairs):raise ValueError('Provide distinct paired task results')
            if any(x.get('verdict') not in ('better','tie','worse') or not isinstance(x.get('regressions'),list) for x in pairs):
                raise ValueError('Each pair needs a verdict and explicit regressions')
        better=sum(x['verdict']=='better' for x in pairs)
        worse=sum(x['verdict']=='worse' for x in pairs)
        accepted=not no_action and better>worse and not any(x['regressions'] for x in pairs)
        files=[]
        if evidence_file:
            record,path=p._store_file(root,evidence_file,'comparison.json');files.append(path)
        else:record=None
        value={'round':s['round'],'accepted':accepted,'no_action':no_action,
               'verdict':'NO_ACTION' if no_action else 'ACCEPT' if accepted else 'REJECT',
               'skill':candidate['skill'] if accepted else s['current_skill'],
               'candidate_skill':candidate['skill'],'pairs':pairs,'reason':reason,
               'evidence':record,'incumbent_score':None,'candidate_score':None,'improvement':None,
               'policy':'lightweight_pairwise'}
        p._event(root,s,'feedback_gate',value,files)
    return work(root)
