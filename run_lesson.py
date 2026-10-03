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
launch = subprocess.Popen(['ros2','launch','nav2_bringup','tb3_loopback_simulation.launch.py',
    'use_rviz:=False','use_composition:=False',f'map:={out / "room.yaml"}'],
    stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result = {'simulation':'Upstream Nav2 loopback; idealized motion, no physical robot', 'goals':[]}
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
    os.killpg(launch.pid,signal.SIGINT) if launch.poll() is None else None
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
    result['launch_exit_code']=launch.returncode
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    print('Evidence:',out,flush=True)
sys.exit(0 if result.get('success') else 1)
