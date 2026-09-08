"""Native-host handoffs. The host creates subagents; this module never calls a model."""
from pathlib import Path
from importlib.resources import files
from . import product as p

RUNTIMES = ('codex', 'claude-code')
RESOURCES = files('wikiskill').joinpath('resources/product')


def install(project, runtime):
    if runtime not in RUNTIMES:
        raise ValueError('Choose codex or claude-code')
    project = Path(project).resolve()
    host = '.codex' if runtime == 'codex' else '.claude'
    targets = []
    for source in RESOURCES.joinpath('agents', runtime).iterdir():
        targets.append((project/host/'agents'/source.name, source.read_bytes()))
    # The same entry skill is packaged for source-independent installation.
    skill_root = project/('.agents' if runtime == 'codex' else '.claude')/'skills'/'wikiskill'
    def gather(source, destination):
        for child in source.iterdir():
            if child.is_dir():
                gather(child, destination/child.name)
            else:
                targets.append((destination/child.name, child.read_bytes()))
    gather(RESOURCES.joinpath('entry-skill'), skill_root)
    for target, data in targets:
        if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent != project):
            raise ValueError('Choose regular host configuration paths, not symlinks: '+str(target))
        if target.exists() and (not target.is_file() or target.read_bytes() != data):
            raise ValueError('Existing host asset differs; review/back up before replacing: '+str(target))
    created = []
    for target, data in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open('xb') as handle:
                handle.write(data)
            created.append(str(target))
    return {'runtime': runtime, 'project': str(project), 'created': created,
            'roles': ['wikiskill-executor', 'wikiskill-maintainer', 'wikiskill-proposer'],
            'entry_skill': str(skill_root/'SKILL.md'),
            'next': 'Reload host agent discovery if needed, then ask the WikiSkill skill to run one round using fresh native subagents.',
            'note': 'Files installed only; no permissions, model defaults or global configuration changed.'}


def _absolute_record(root, record):
    return {**record, 'file': str(root/record['file'])} if record else None


def _learning_context(root, state):
    context = p._context(root, state)
    context['current_skill'] = _absolute_record(root, context['current_skill'])
    for row in context['training_records']:
        row['output'] = _absolute_record(root, row['output'])
        row['trace'] = _absolute_record(root, row['trace'])
    context['human_feedback'] = [{**row, 'file': str(root/row['file'])} for row in context['human_feedback']]
    context['gate_history'] = [{k: row[k] for k in ('round','verdict','incumbent_score','candidate_score','improvement')}
                               for row in state['history']]
    return context


def dispatch(root, runtime, count=1):
    if runtime not in RUNTIMES:
        raise ValueError('Choose codex or claude-code')
    root = Path(root).resolve()
    state = p._load(root)
    if state['config'].get('agent_runtime') != runtime:
        raise ValueError('Runtime differs from the configured comparison; start a new workspace with --agent-runtime '+runtime)
    work = p.next_work(root, count)
    handoffs = []
    for request in work.get('requests', []):
        with p.locked(root):
            state = p._load(root)
            request = state['requests'][request['id']]
            if not request.get('handoff') and request.get('previous_output'):
                previous = state['requests'][request['retry_of']]
                if previous.get('delegation'):
                    if previous['delegation']['runtime'] != runtime:
                        raise ValueError('Scoring retry must retain the original executor runtime')
                    handoff = {'request_id':request['id'],'runtime':runtime,'role':'wikiskill-executor',
                               'context_mode':'fresh','reused_output':str(root/request['previous_output']['file']),
                               'reused_from':previous['id'],'message':'Reuse saved execution; collect this request without spawning another agent.'}
                    state=p._event(root,state,'handoff',handoff)
                    delegation={**previous['delegation'],'request_id':request['id'],'reused_from':previous['id']}
                    state=p._event(root,state,'delegated',delegation)
                    request=state['requests'][request['id']]
            if request.get('handoff'):
                handoff = request['handoff']
                if handoff['runtime'] != runtime:
                    raise ValueError('This request already has a different host handoff')
            else:
                role = 'executor' if request['kind'] == 'task' else request['kind']
                directory = root/'requests'/request['id']/'agent'
                directory.mkdir(parents=True, exist_ok=True)
                output = directory/'output'
                output.mkdir(exist_ok=True)
                payload = {'role': role, 'output_directory': str(output)}
                assets = []
                if role == 'executor':
                    # Never include previous_output, scores, baseline answers or the learning Wiki.
                    payload.update(task=request['task'], skill=_absolute_record(root, request['skill']))
                else:
                    context_file = directory/'learning-context.json'
                    p.write(context_file, _learning_context(root, state), immutable=True)
                    payload['context_file'] = str(context_file)
                    assets.append(context_file)
                payload_file = directory/'payload.json'
                p.write(payload_file, payload, immutable=True)
                prompt_file = directory/'role.md'
                prompt = RESOURCES.joinpath('roles', role+'.md').read_text(encoding='utf-8')
                if prompt_file.exists() and prompt_file.read_text(encoding='utf-8') != prompt:
                    raise ValueError('Existing role handoff differs; preserve it and inspect the interrupted dispatch')
                prompt_file.write_text(prompt, encoding='utf-8')
                assets += [payload_file, prompt_file]
                handoff = {'request_id': request['id'], 'runtime': runtime, 'role': 'wikiskill-'+role,
                           'prompt_file': str(prompt_file), 'payload_file': str(payload_file),
                           'output_directory': str(output), 'result_file': str(output/'result.json'),
                           'context_mode': 'fresh',
                           'message': f'Read role instructions at {prompt_file} and execute only the payload at {payload_file}. Return the result.json path. Do not inherit the coordinator conversation.'}
                p._event(root, state, 'handoff', handoff, assets)
            request=p._load(root)['requests'][request['id']]
            handoffs.append({**handoff, 'delegation': request.get('delegation')})
    return {'workspace': str(root), 'phase': work['phase'], 'handoffs': handoffs,
            'action': 'Use the host native subagent tool with fresh context. Bind its actual returned ID, wait, then collect. Do not launch another model CLI.' if handoffs else work.get('action'),
            'failures': work.get('failures', [])}


def bind(root, request_id, agent_id, runtime, context_mode):
    if runtime not in RUNTIMES or context_mode != 'fresh' or not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError('Record the actual host agent ID, supported runtime and fresh context')
    with p.locked(root) as root:
        state = p._load(root)
        request = state['requests'].get(request_id)
        if not request or request['status'] != 'pending' or not request.get('handoff'):
            raise ValueError('Dispatch a pending request before binding a subagent')
        if request['handoff']['runtime'] != runtime:
            raise ValueError('Agent runtime differs from handoff')
        value = {'request_id': request_id, 'agent_id': agent_id, 'runtime': runtime,
                 'context_mode': context_mode, 'evidence': 'host-reported; not independent attestation'}
        if request.get('delegation'):
            if request['delegation'] != value:
                raise ValueError('Request already bound; resume its existing agent or explicitly fail/retry')
            return value
        if any(r.get('delegation', {}).get('agent_id') == agent_id and r.get('delegation', {}).get('runtime') == runtime
               for r in state['requests'].values()):
            raise ValueError('Use a new subagent for each request; this agent ID was already used')
        p._event(root, state, 'delegated', value)
        return value


def fail(root, request_id, error):
    if not isinstance(error, str) or not error.strip():
        raise ValueError('Describe the execution or delegation failure')
    with p.locked(root) as root:
        state = p._load(root)
        request = state['requests'].get(request_id)
        if not request or request['status'] != 'pending':
            raise ValueError('Only a pending request can fail')
        return p._status(root, p._event(root, state, 'failure', {'request_id': request_id, 'error': error}))


def collect(root, request_id, *, score=None, feedback='', success=None):
    root = Path(root).resolve()
    state = p._load(root)
    request = state['requests'].get(request_id)
    if not request or not request.get('handoff') or not request.get('delegation'):
        raise ValueError('Dispatch and bind the native subagent before collecting')
    if request['status'] == 'complete':
        return p.status(root)  # Already sealed: never rescore/reapply a changed scratch result.
    if request['status'] != 'pending':
        raise ValueError('Resolve the failure and explicitly retry before collecting')
    if request['handoff'].get('reused_output'):
        return p.record(root,request_id,output=request['handoff']['reused_output'],score=score,feedback=feedback,
                        success=success,runtime=request['delegation']['runtime'])
    output = Path(request['handoff']['output_directory']).resolve()
    def own(path):
        value = Path(path)
        value = (output/value).resolve() if not value.is_absolute() else value.resolve()
        if not value.is_relative_to(output) or not value.is_file():
            raise ValueError('Subagent output must be a file in this request output directory')
        return value
    result_path = own(request['handoff']['result_file'])
    result = p.read(result_path)
    if not isinstance(result, dict):
        raise ValueError('Subagent result.json must contain an object')
    if 'error' in result:
        return fail(root, request_id, result['error'])
    if request['kind'] == 'task':
        return p.record(root, request_id, output=own(result['output']),
                        trace=own(result['trace']) if result.get('trace') else None,
                        score=score, feedback=feedback, success=success,
                        runtime=request['delegation']['runtime'])
    if request['kind'] == 'maintainer':
        return p.learn(root, request_id, result_path)
    if result.get('no_action') is True:
        if result.get('skill'):
            raise ValueError('Choose a candidate or no_action, not both')
        return p.propose(root, request_id, no_action=True, note=result.get('note', ''))
    return p.propose(root, request_id, skill=own(result['skill']), note=result.get('note', ''))
