"""Failure/success-balanced sampling and current visible tool trajectories."""
from pathlib import Path
import json
import random

from wikiskill.jsonl import read_jsonl


def sample(rows,seed):
    if any(r['split']!='train' for r in rows):raise ValueError('Only training trajectories may enter Wiki')
    rng=random.Random(seed)
    failed=sorted((r for r in rows if r['score']==0),key=lambda r:r['uid'])
    passed=sorted((r for r in rows if r['score']==1),key=lambda r:r['uid'])
    selected=rng.sample(failed,min(5,len(failed)))+rng.sample(passed,min(3,len(passed)))
    return selected


def visible_trace(row,question,limit=15000):
    archive=Path(row['workspace'])/'runtime'
    visible={k:question[k] for k in ('question','instruction_type','answer_position','answer_sheet') if k in question} if isinstance(question,dict) else {'question':question}
    parts=[f"Task {row['uid']}\nResult: {'PASS' if row['score']==1 else 'FAIL'}\nTask input: "+json.dumps(visible,ensure_ascii=False)+'\n']
    receipts=read_jsonl(archive/'tool-events.jsonl') if (archive/'tool-events.jsonl').exists() else []
    if receipts:
        for event in receipts:
            parts.append('TOOL '+event['tool']+'\nARGS '+json.dumps(event['arguments'],ensure_ascii=False)+'\nRESULT '+json.dumps(event.get('result',event.get('error')),ensure_ascii=False)+'\n')
    else:
        for e in read_jsonl(archive/'session.jsonl'):
            p=e.get('payload',{});kind=p.get('type')
            if e.get('type')=='response_item' and kind in ('function_call','custom_tool_call','function_call_output','custom_tool_call_output'):
                parts.append(json.dumps(p,ensure_ascii=False)+'\n')
    parts.append('FINAL\n'+row['predicted'])
    text='\n'.join(parts)
    if len(text)>limit:
        marker='\n[Middle of visible trace omitted at the frozen 15000-character limit.]\n'
        tail=4000;text=text[:limit-tail-len(marker)]+marker+text[-tail:]
    return text
