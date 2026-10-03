"""Signal the real manager while its first lifecycle service is absent."""
import json
import os
import resource
from pathlib import Path
import signal
import subprocess
import sys
import time

root=Path(__file__).resolve().parent
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
variant=sys.argv[1]
if variant not in ('baseline','shutdown-cancellation','shutdown-coordinated','upstream-jazzy','upstream-main','main-coordinated'):
    raise SystemExit('Unknown variant')
prefix=Path('/home/learner/nav2-shutdown-build')/variant/'install'
out=root/'results'/('discovery-'+str(time.time_ns()))
out.mkdir(parents=True)
env=os.environ.copy()
env['ROS_DOMAIN_ID']='74'
env['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
dependency='upstream-main' if variant=='main-coordinated' else 'baseline'
env['LD_LIBRARY_PATH']=str(prefix/'lib')+f':/home/learner/nav2-shutdown-build/{dependency}/install/lib:'+env.get('LD_LIBRARY_PATH','')
delay=float(sys.argv[2]) if len(sys.argv)>2 else 0.5
if not 0 <= delay <= 10: raise SystemExit('Delay must be between 0 and 10 seconds')
result={'variant':variant,'mode':'discovery','delay_after_initialization_log':delay,'graceful_manager_shutdown':False}
with (out/'process.log').open('w') as log:
    manager=subprocess.Popen([str(prefix/'lib/nav2_lifecycle_manager/lifecycle_manager'),
        '--ros-args','-p','node_names:=[intentionally_absent_probe_server]',
        '-p','autostart:=True'],stdout=log,stderr=log,env=env,start_new_session=True)
    try:
        deadline=time.monotonic()+10
        while 'Creating and initializing lifecycle service clients' not in (out/'process.log').read_text():
            if manager.poll() is not None or time.monotonic()>deadline:
                raise RuntimeError('Manager did not reach client initialization')
            time.sleep(0.05)
        time.sleep(delay)
        result['missing_service_setup_confirmed']=True
        result['loaded_nav2_libraries']=sorted(set(s.split()[-1] for s in Path(f'/proc/{manager.pid}/maps').read_text().splitlines() if '/libnav2_' in s))
        start=time.monotonic()
        manager.send_signal(signal.SIGINT)
        try:
            manager.wait(timeout=5)
            result['exit_code']=manager.returncode
            result['graceful_manager_shutdown']=manager.returncode==0
        except subprocess.TimeoutExpired:
            result['manager_alive_after_5_seconds']=True
        result['shutdown_seconds']=round(time.monotonic()-start,3)
    except Exception as exc:
        result['error']=str(exc)
    finally:
        if manager.poll() is None:
            manager.kill(); manager.wait(timeout=3)
(out/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result)); print(out)
sys.exit(0 if result['graceful_manager_shutdown'] else 1)
