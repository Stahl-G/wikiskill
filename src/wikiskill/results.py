"""Recompute the bundled validation snapshot without models or benchmark data."""
from pathlib import Path
from hashlib import sha256
import json
from .settings import RESOURCES


def verify(directory=None):
    root=Path(directory) if directory else RESOURCES/'research'
    path=root/'snapshot.json'
    expected=(root/'snapshot.sha256').read_text().strip()
    if sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Snapshot checksum mismatch')
    data=json.loads(path.read_text())
    summary=[]
    for c in data['cells']:
        if c['baseline'] is None:continue
        rows=[p for p in data['pairs'] if p['domain']==c['domain'] and p['arm']==c['arm']]
        if len(rows)!=c['val_n'] or len({r['uid'] for r in rows})!=len(rows):raise ValueError('Incomplete or duplicated pairs')
        a=sum(x['s0'] for x in rows)/len(rows);b=sum(x['retained_val'] for x in rows)/len(rows)
        if abs(a-c['baseline'])>1e-10 or abs(b-c['retained'])>1e-10:raise ValueError('Score mismatch')
        if c['skill'] and sha256((root/c['skill']).read_bytes()).hexdigest()!=c['skill_sha256']:raise ValueError('Skill checksum mismatch')
        summary.append({k:c[k] for k in ['domain','arm','val_n','baseline','retained','status']})
    return {'verified':True,'captured_at':data['captured_at'],'scope':data['scope'],'cells':summary}
