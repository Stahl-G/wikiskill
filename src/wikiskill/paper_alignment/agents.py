"""Paper role adapters for the existing engine; no evolutionary loop here.

The original appendix prompts are the sole behavioral instructions. Handoffs
contain paths and visibility facts only, never retry or outcome directives.
"""
from pathlib import Path
import hashlib
import json
from . import contracts, evidence
from wikiskill import engine
from wikiskill.skill_proposer import ProposalPurpose, ProposalResult, _unified_diff

PROMPTS=Path(__file__).resolve().parents[1]/'resources/paper_alignment/prompts'

def paper_prompts(task_description):
    return {role+'.md':(PROMPTS/(role+'.paper.md')).read_text().replace('{task_desc}',task_description)
            for role in ('maintainer','proposer')}

def handoff(iteration,skills):
    return json.dumps({'iteration':iteration,'wiki_index':'wiki/index.md',
                      'skill_impact':'wiki/skill-impact.md','active_skills_file':'skills.json',
                      'training_trace_index':'trace-summary.json',
                      'executor_visibility':{'wiki':False,'active_skill_names':sorted(skills)}},sort_keys=True)

class PaperAgents:
    """Use an injected isolated invocation transport and optional TRAIN feedback.

    invoke(directory, payload, system, user, mode, model, effort) returns an
    archive containing validated submission.json, final.txt, and tool receipts.
    No benchmark data, credentials or host transport are imported implicitly.
    """
    def __init__(self,invoke,*,seed=0,training_feedback=None):
        self.invoke=invoke;self.seed=seed;self.training_feedback=training_feedback

    def _rows(self,paths):
        rows=[json.loads(line) for p in paths for line in Path(p).read_text().splitlines() if line.strip()]
        if not rows or any(r.get('split')!='train' for r in rows):raise ValueError('Paper learning roles require TRAIN only')
        if len({r['uid'] for r in rows})!=len(rows):raise ValueError('Duplicate training UID')
        return rows

    def _skills(self,wiki_dir,current):
        if not current:return {}
        root=Path(wiki_dir).parent
        accepted=[r for r in engine.events(root) if r.get('type')=='gate' and r.get('accepted')]
        if not accepted:raise ValueError('Missing accepted paper skill mapping')
        iteration=accepted[-1]['iteration']
        skills=json.loads((root/f'iterations/{iteration:03d}/proposer/paper-candidate.json').read_text())
        if contracts.skill_text(skills)!=current:raise ValueError('Accepted skill text/map mismatch')
        return skills

    def _payload(self,wiki_dir,rows,skills):
        # Prompts remain control input, not editable Wiki pattern content.
        wiki={k:v for k,v in contracts.read_wiki(Path(wiki_dir)).items() if not k.startswith('prompts/')}
        wiki.setdefault('log.md',wiki.get('logs.md','# Evolution log\n'))
        payload={'wiki/'+k:v for k,v in wiki.items()}
        payload['skills.json']=json.dumps(skills)
        summaries=[]
        for row in rows:
            text=evidence.visible_trace(row,row['question'])
            if self.training_feedback:
                text+='\nTRAIN evaluator feedback:\n'+json.dumps(self.training_feedback(row),ensure_ascii=False)
            path='traces/'+row['uid']+'.md';payload[path]=text
            summaries.append({'uid':row['uid'],'split':'train','score':row['score'],'path':path})
        payload['trace-summary.json']=json.dumps(summaries,ensure_ascii=False)
        return payload,wiki

    def maintainer_factory(self,*,model,workdir,reasoning_effort):
        def run(paths,*,iteration,wiki_dir):
            root=Path(wiki_dir).parent;state=engine.state(root)
            current=(root/state['skill']).read_text();skills=self._skills(wiki_dir,current)
            rows=evidence.sample(self._rows(paths),self.seed+iteration)
            payload,wiki=self._payload(wiki_dir,rows,skills)
            system=(Path(wiki_dir)/'prompts/maintainer.md').read_text()
            archive=Path(self.invoke(Path(workdir),payload,system,handoff(iteration,skills),'maintainer',model,reasoning_effort))
            value=json.loads((archive/'submission.json').read_text())['proposal']
            normalized,updated=contracts.wiki_update(value,wiki)
            updated['log.md']=wiki.get('log.md','')+'\n'+normalized['append_log']+'\n'
            for name,text in updated.items():
                path=Path(wiki_dir)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
            return normalized
        return run

    def proposer_factory(self,*,model,workdir,reasoning_effort):
        def run(current,paths,*,iteration,wiki_dir):
            skills=self._skills(wiki_dir,current);payload,_=self._payload(wiki_dir,self._rows(paths),skills)
            system=(Path(wiki_dir)/'prompts/proposer.md').read_text();user=handoff(iteration,skills)
            archive=Path(self.invoke(Path(workdir),payload,system,user,'proposer',model,reasoning_effort))
            submitted=json.loads((archive/'submission.json').read_text())
            value,candidate=contracts.proposal(submitted['proposal'],skills,submitted['read_trace_ids'])
            # Check actual successful reads as well as the submitted receipt.
            receipts=[json.loads(x) for x in (archive/'tool-events.jsonl').read_text().splitlines()]
            reads={Path(r['arguments']['path']).stem for r in receipts if r.get('ok') and r.get('tool')=='read_file' and r.get('arguments',{}).get('path','').startswith('traces/')}
            if value['action']!='no_action' and len(reads)<4:raise ValueError('Fewer than four actual training trace reads')
            engine.save(Path(workdir)/'paper-candidate.json',candidate)
            text=contracts.skill_text(candidate) if value['action']!='no_action' else ''
            return ProposalResult(action='no_action' if value['action']=='no_action' else 'skill',skill_md=text,
                                  purpose=ProposalPurpose(summary=value.get('purpose_md','')),
                                  rationale=(archive/'final.txt').read_text(),
                                  prompt_sha256=hashlib.sha256((system+user).encode()).hexdigest(),
                                  diff=_unified_diff(current,text),stdout_path=archive/'final.txt')
        return run
