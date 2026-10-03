"""Exercise discovery timings and existing service-wait paths, serially."""
import json
from pathlib import Path
import subprocess
import time

root=Path(__file__).resolve().parent
target=root/'results'/('coordinated-matrix-'+str(time.time_ns())+'.json')
report={'candidate':'shutdown-coordinated','trials':[]}
def run(command,pattern,expected):
    before=set((root/'results').glob(pattern))
    result=subprocess.run(command,timeout=60)
    created=set((root/'results').glob(pattern))-before
    if len(created)!=1: raise RuntimeError('Cannot identify probe output')
    folder=created.pop()
    evidence=json.loads((folder/'result.json').read_text())
    valid=(evidence.get('graceful_manager_shutdown') is True if expected==0 else
           evidence.get('missing_service_setup_confirmed') is True and evidence.get('exit_code')==-6)
    report['trials'].append({'run':folder.name,'expected_exit_code':expected,
        'actual_exit_code':result.returncode,'expectation_met':result.returncode==expected and valid,
        'result':evidence,
        'log':(folder/'process.log').read_text()})
    target.write_text(json.dumps(report,indent=2))
    print('MATRIX',folder.name,'expectation met',result.returncode==expected,flush=True)

for variant in ('baseline','shutdown-cancellation'):
    run(['python3',str(root/'probe_discovery.py'),variant,'0.5'],'discovery-*',1)
for repeat in range(3):
    for delay in ('0','0.005','0.05','0.5','2'):
        run(['python3',str(root/'probe_discovery.py'),'shutdown-coordinated',delay],'discovery-*',0)
for mode in ('alive','dead','transition','slow'):
    run(['bash',str(root/'probe_shutdown_variant.sh'),'shutdown-coordinated',mode],'shutdown-'+mode+'-*',0)
report['success']=all(t['expectation_met'] for t in report['trials'])
target.write_text(json.dumps(report,indent=2))
print(target,flush=True)
raise SystemExit(0 if report['success'] else 1)
