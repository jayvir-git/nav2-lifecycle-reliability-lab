"""Controlled fault followed by deliberate full-stack restart recovery."""
import json
from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parent
runs=[]
for label,args in [('fault',['--fault']),('recovery',[])]:
    before=set((root/'results').glob('*'))
    result=subprocess.run([sys.executable,str(root/'run_lesson.py'),*args],timeout=300)
    created=set((root/'results').glob('*'))-before
    if len(created)!=1: raise RuntimeError('Cannot identify experiment output')
    path=created.pop()
    lines=(path/'launch.log').read_text().splitlines()
    excerpts=[line for line in lines if any(term in line for term in
        ['Aborting handle', 'Have not received a heartbeat', 'CRITICAL FAILURE', 'failed to terminate'])]
    runs.append({'phase':label,'run':path.name,'result':json.loads((path/'summary.json').read_text()),
                 'log_excerpts':excerpts, 'forced_shutdown_observed':any('failed to terminate' in line for line in lines)})
    if result.returncode: break
report={'recovery_method':'Deliberate full-stack restart with pose reset; not automatic recovery or in-place controller restart',
        'runs':runs,'success':len(runs)==2 and all(r['result']['success'] for r in runs)}
if len(runs)==2:
    fault=runs[0]['result']
    report['checks']={
        'navigation_aborted':fault.get('action_status')==6,
        'planner_observed_inactive':any(s['node']=='planner_server' and s['state']=='inactive' for s in fault.get('state_samples',[])),
        'navigator_observed_inactive':any(s['node']=='bt_navigator' and s['state']=='inactive' for s in fault.get('state_samples',[])),
        'restart_navigation_succeeded':runs[1]['result'].get('success',False)}
    report['success']=report['success'] and all(report['checks'].values())
report['success_meaning']='Fault observation and restart checks passed; does not imply graceful shutdown.'
target=root/'results'/('failure-experiment-'+runs[0]['run']+'.json')
target.write_text(json.dumps(report,indent=2))
print('Combined evidence:',target,flush=True)
sys.exit(0 if report['success'] else 1)
