"""Operate upstream Nav2; record a bounded first navigation lesson."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import threading

ROOT = Path(__file__).resolve().parent
lock = open('/tmp/nav2-first-lesson.lock', 'w')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit('Another copy of this lesson is running.')
out = ROOT / 'results' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out.mkdir(parents=True)
# A known, simple room: 10x10m, with occupied boundary walls. No physics claim.
n = 200
pixels = bytes(0 if x < 3 or y < 3 or x >= n-3 or y >= n-3 else 254
               for y in range(n) for x in range(n))
(out / 'room.pgm').write_bytes(f'P5\n{n} {n}\n255\n'.encode() + pixels)
(out / 'room.yaml').write_text('image: room.pgm\nresolution: 0.05\norigin: [-5.0, -5.0, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')
log = (out / 'launch.log').open('w')
resource_stop=threading.Event()
resources={'scope':'Aggregate WSL guest CPU and memory; not Windows host utilization',
           'cpu_count':os.cpu_count(),'samples':[]}
def sample_resources():
    previous=None
    started=time.monotonic()
    while not resource_stop.is_set():
        try:
            cpu=[int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
            total=sum(cpu); idle=cpu[3]+cpu[4]
            memory={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
            sample={'seconds':round(time.monotonic()-started,2),'memory_available_kib':memory['MemAvailable'],
                    'memory_total_kib':memory['MemTotal'],'load_1m':os.getloadavg()[0]}
            if previous and total>previous[0]:
                sample['cpu_busy_percent']=round(100*(1-(idle-previous[1])/(total-previous[0])),2)
            resources['samples'].append(sample)
            previous=(total,idle)
        except (OSError,ValueError,KeyError) as exc:
            resources['sampling_error']=str(exc)
            break
        resource_stop.wait(1)
resource_thread=threading.Thread(target=sample_resources,daemon=True)
resource_thread.start()
launch = subprocess.Popen(['ros2','launch','nav2_bringup','tb3_loopback_simulation.launch.py',
    'use_rviz:=False','use_composition:=False',f'map:={out / "room.yaml"}'],
    stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result = {'simulation':'Upstream Nav2 loopback; idealized motion, no physical robot', 'goals':[],
          'variant':os.environ.get('NAV2_PROBE_VARIANT','installed')}
try:
    fault = '--fault' in sys.argv
    mission_script = 'fault_mission.py' if fault else 'mission.py'
    mission = subprocess.run([sys.executable,str(ROOT/mission_script),str(out),str(launch.pid)],timeout=240)
    result.update(json.loads((out/'mission.json').read_text()) if (out/'mission.json').exists() else {})
    result['mission_exit_code'] = mission.returncode
    for label,args in [('nodes',['ros2','node','list']),('topics',['ros2','topic','list','-t']),
                       ('packages',['dpkg-query','-W','ros-jazzy-nav2*']),('processes',['ps','-eo','pid,ppid,args'])]:
        capture=subprocess.run(args,capture_output=True,text=True,timeout=15)
        (out/f'{label}.txt').write_text(capture.stdout + capture.stderr)
    result['success'] = mission.returncode == 0
except Exception as exc:
    result['success'] = False
    result['error'] = str(exc)
finally:
    # Let ROS launch forward one interrupt to its children. Signalling the whole
    # group here also delivers a second interrupt during child teardown.
    launch.send_signal(signal.SIGINT) if launch.poll() is None else None
    try: launch.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(launch.pid,signal.SIGKILL)
        launch.wait(timeout=5)
    # A failed launch can exit before its children. Clean only our own session's
    # process group, even when the launcher itself has already exited.
    result['residual_group_cleanup_needed'] = False
    try:
        os.killpg(launch.pid, 0)
        result['residual_group_cleanup_needed'] = True
        os.killpg(launch.pid, signal.SIGTERM)
        time.sleep(1)
        try: os.killpg(launch.pid, signal.SIGKILL)
        except ProcessLookupError: pass
    except ProcessLookupError:
        pass
    log.close()
    resource_stop.set(); resource_thread.join(timeout=2)
    (out/'resources.json').write_text(json.dumps(resources,indent=2))
    result['launch_exit_code']=launch.returncode
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    print('Evidence:',out,flush=True)
sys.exit(0 if result.get('success') else 1)
