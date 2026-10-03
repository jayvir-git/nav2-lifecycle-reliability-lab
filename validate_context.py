"""Bounded subprocess tests of public manager/context APIs, no source test hooks."""
import json
import os
from pathlib import Path
import subprocess
import platform
import time

root=Path(__file__).resolve().parent
base=Path(os.environ.get('NAV2_LAB_BUILD_ROOT','/home/learner/nav2-shutdown-build'))
env=os.environ.copy()
env['LD_LIBRARY_PATH']=f'{base}/main-coordinated/install/lib:{base}/upstream-main/install/lib:'+env.get('LD_LIBRARY_PATH','')
env['ROS_DOMAIN_ID']='74'
env['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
report={'runtime':{'ros_distro':env.get('ROS_DISTRO'),'kernel':platform.release()},'trials':[]}
target=root/'results'/('context-matrix-'+str(time.time_ns())+'.json')
target.parent.mkdir(exist_ok=True)
for repeat in range(3):
    for mode,delay in [('before-spin',0)]+[(m,d) for m in ('discovery','empty') for d in (0,5,50)]:
        env['ROS_DOMAIN_ID']=str(120+len(report['trials']))
        try:
            p=subprocess.run([str(base/'context-probe/context_probe'),mode,str(delay)],
                             env=env,text=True,capture_output=True,timeout=12)
            trial={'mode':mode,'delay_ms':delay,'exit_code':p.returncode,
                   'passed':p.returncode==0 and 'CONTEXT_SHUTDOWN_OK' in p.stdout,
                   'stdout':p.stdout,'stderr':p.stderr}
        except subprocess.TimeoutExpired as exc:
            trial={'mode':mode,'delay_ms':delay,'passed':False,'error':'12-second process timeout',
                   'stdout':str(exc.stdout),'stderr':str(exc.stderr)}
        report['trials'].append(trial)
        target.write_text(json.dumps(report,indent=2))
report['success']=all(t['passed'] for t in report['trials'])
target.write_text(json.dumps(report,indent=2))
print(target,flush=True)
raise SystemExit(0 if report['success'] else 1)
