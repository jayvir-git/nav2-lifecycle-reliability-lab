"""Run bounded regression probes against pinned main and the isolated port."""
import json
from pathlib import Path
import subprocess
import time
import os
import platform
import argparse

parser=argparse.ArgumentParser()
parser.add_argument('--fault-pairs',type=int,choices=range(1,6),default=1)
args=parser.parse_args()

root=Path(__file__).resolve().parent
target=root/'results'/('main-matrix-'+str(time.time_ns())+'.json')
target.parent.mkdir(exist_ok=True)
report={'source_sha':'d7bf2ac06fe778c21c6141eb49b4d3e2c0c82d3a',
        'runtime':{'ros_distro':os.environ.get('ROS_DISTRO'), 'kernel':platform.release(),
                   'ci':os.environ.get('GITHUB_ACTIONS','false')},'trials':[]}

def run(command,pattern,expected=0):
    before=set((root/'results').glob(pattern))
    env=os.environ.copy()
    # Isolate sequential DDS experiments; stale discovery from prior trials must not participate.
    env['NAV2_LAB_DOMAIN_ID']=str(74+len(report['trials']))
    process=subprocess.run(command,timeout=65,env=env)
    created=set((root/'results').glob(pattern))-before
    if len(created)!=1: raise RuntimeError('Ambiguous probe output')
    folder=created.pop()
    result=json.loads((folder/'result.json').read_text())
    valid=(result.get('graceful_manager_shutdown') is True if expected==0 else
           result.get('bond_loss_detected') is True and result.get('manager_alive_after_5_seconds') is True)
    report['trials'].append({'run':folder.name,'expectation_met':process.returncode==expected and valid,
                            'result':result,'log':(folder/'process.log').read_text()})
    target.write_text(json.dumps(report,indent=2))

for mode in ('alive','dead'):
    run(['bash',str(root/'probe_shutdown_variant.sh'),'upstream-main',mode],
        'shutdown-'+mode+'-*',0 if mode=='alive' else 1)
for repeat in range(2):
    for delay in ('0','0.05','2'):
        run(['python3',str(root/'probe_discovery.py'),'main-coordinated',delay],'discovery-*')
for mode in ('alive','dead','transition','slow'):
    run(['bash',str(root/'probe_shutdown_variant.sh'),'main-coordinated',mode], 'shutdown-'+mode+'-*')
for repeat in range(args.fault_pairs-1):
    for variant in ('upstream-main','main-coordinated'):
        run(['bash',str(root/'probe_shutdown_variant.sh'),variant,'dead'], 'shutdown-dead-*',
            1 if variant=='upstream-main' else 0)
report['success']=all(t['expectation_met'] for t in report['trials'])
target.write_text(json.dumps(report,indent=2))
print(target,flush=True)
raise SystemExit(0 if report['success'] else 1)
