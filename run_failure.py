"""Controlled fault followed by deliberate full-stack restart recovery."""
import json
import re
import os
from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parent
runs=[]
for label,args in [('fault',['--fault']),('recovery',[])]:
    before=set((root/'results').glob('20??????T??????Z'))
    result=subprocess.run([sys.executable,str(root/'run_lesson.py'),*args],timeout=300)
    created=set((root/'results').glob('20??????T??????Z'))-before
    if len(created)!=1: raise RuntimeError('Cannot identify experiment output')
    path=created.pop()
    lines=(path/'launch.log').read_text().splitlines()
    excerpts=[line for line in lines if any(term in line for term in
        ['Aborting handle', 'Have not received a heartbeat', 'CRITICAL FAILURE', 'failed to terminate'])]
    manager_labels=set(re.findall(r'\[(lifecycle_manager-\d+)\]: process started', '\n'.join(lines)))
    clean_labels=set(re.findall(r'\[(lifecycle_manager-\d+)\]: process has finished cleanly', '\n'.join(lines)))
    runs.append({'phase':label,'run':path.name,'result':json.loads((path/'summary.json').read_text()),
                 'log_excerpts':excerpts, 'forced_shutdown_observed':any('failed to terminate' in line for line in lines),
                 'lifecycle_managers_clean_exit':bool(manager_labels) and manager_labels.issubset(clean_labels)})
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
    if os.environ.get('NAV2_PROBE_VARIANT')=='shutdown-cancellation':
        report['checks']['no_forced_shutdown']=all(not r['forced_shutdown_observed'] for r in runs)
        report['checks']['lifecycle_managers_clean_exit']=all(r['lifecycle_managers_clean_exit'] for r in runs)
        report['success']=report['success'] and all(report['checks'].values())
report['success_meaning']=(
    'Success requires fault observation, restart navigation, and clean lifecycle-manager exit checks.'
    if os.environ.get('NAV2_PROBE_VARIANT')=='shutdown-cancellation' else
    'Success requires fault observation and restart checks; does not imply graceful shutdown.')
target=root/'results'/('failure-experiment-'+runs[0]['run']+'.json')
target.write_text(json.dumps(report,indent=2))
print('Combined evidence:',target,flush=True)
sys.exit(0 if report['success'] else 1)
