"""Create a compact, auditable notebook summary from a completed repeat batch."""
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parent
source=Path(sys.argv[1])
batch=json.loads(source.read_text())
rows=[]
for run in batch['runs']:
    phases=[]
    for phase in run['result']['runs']:
        result=phase['result']
        phases.append({k:phase[k] for k in ['phase','run','forced_shutdown_observed','lifecycle_managers_clean_exit']})
        phases[-1]['result']={k:result[k] for k in ['success','error','initial_states','events','lifecycle','action_status','mission_exit_code','launch_exit_code','residual_group_cleanup_needed'] if k in result}
        phases[-1]['goals']=[{k:g[k] for k in ['target','status','seconds']} for g in result.get('goals',[])]
    samples=[s for resource in run['resources'] for s in resource['samples']]
    rows.append({'pair':run['pair'],'variant':run['variant'],'success':run['result']['success'],
        'checks':run['result'].get('checks',{}),'evidence_file':run['evidence_file'],'phases':phases,
        'response_delivery_warnings':run['response_delivery_warnings'],
        'resource_summary':{'scope':'Aggregate WSL guest; no claim about individual thread starvation or Windows host',
            'cpu_count':run['resources'][0]['cpu_count'],
            'maximum_sampled_cpu_busy_percent':max(s.get('cpu_busy_percent',0) for s in samples),
            'minimum_memory_available_kib':min(s['memory_available_kib'] for s in samples)}})
assert len(rows)==batch['pairs_requested']*2, 'Batch is incomplete'
candidate=batch.get('candidate','shutdown-cancellation')
counts={v:sum(r['success'] for r in rows if r['variant']==v) for v in ['baseline',candidate]}
warnings=sum(len(r['response_delivery_warnings']) for r in rows)
summary={'source_file':source.name,'pairs':batch['pairs_requested'],'completed_sequences':counts,
    'definition':'Baseline success excludes clean shutdown; candidate additionally requires clean lifecycle-manager exits and no launcher escalation.',
    'response_delivery_warning_count':warnings,'runs':rows}
filename='coordinated-reliability.json' if candidate=='shutdown-coordinated' else 'reliability-summary.json'
(root/'docs'/filename).write_text(json.dumps(summary,indent=2))
if candidate=='shutdown-coordinated':
    print(json.dumps({'counts':counts,'warnings':warnings}))
    raise SystemExit(0)
n=batch['pairs_requested']
view={'main_status':'HANG REPRODUCED',
    'main_detail':'Unmodified main-source manager, utilities, and messages built on the Jazzy runtime. Healthy control exited; killed-node control remained alive after five seconds. This is not a native Rolling test.',
    'repeat_title':f"Baseline {counts['baseline']} / {n}; candidate {counts['shutdown-cancellation']} / {n} completed sequences.",
    'repeat_detail':f'{warnings} server response-delivery warnings recorded. Baseline completion includes its expected forced shutdown; candidate completion requires clean manager exits. This small batch does not establish a reliability rate or resolve the earlier intermittent failure.'}
(root/'docs/upstream-data.js').write_text('window.UPSTREAM = '+json.dumps(view)+';\n')
print(json.dumps({'counts':counts,'warnings':warnings}))
