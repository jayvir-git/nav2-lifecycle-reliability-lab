"""Minimal installed-Nav2 shutdown probe: one map server, one manager."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import rclpy
from rclpy.node import Node
from lifecycle_msgs.srv import GetState
from nav2_msgs.srv import ManageLifecycleNodes

root=Path(__file__).resolve().parent
mode=sys.argv[1] if len(sys.argv)>1 else 'dead'
if mode not in ('alive','dead','dead-sim','slow','transition'): raise SystemExit('Unknown probe mode')
out=root/'results'/('shutdown-'+mode+'-'+str(time.time_ns()))
out.mkdir(parents=True)
# Generate the small map locally so the repro does not depend on old results.
(out/'room.pgm').write_bytes(b'P5\n20 20\n255\n'+bytes([254])*400)
(out/'room.yaml').write_text('image: room.pgm\nresolution: 0.05\norigin: [0,0,0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')
os.environ['ROS_DOMAIN_ID']='74'
log=(out/'process.log').open('w')
children=[]
manager_executable=os.environ.get('NAV2_PROBE_MANAGER','/opt/ros/jazzy/lib/nav2_lifecycle_manager/lifecycle_manager')
manager_env=os.environ.copy()
if 'NAV2_PROBE_PREFIX' in os.environ:
    dependency='upstream-main' if os.environ.get('NAV2_PROBE_VARIANT')=='main-coordinated' else 'baseline'
    build_root=os.environ.get('NAV2_LAB_BUILD_ROOT','/home/learner/nav2-shutdown-build')
    manager_env['LD_LIBRARY_PATH']=os.environ['NAV2_PROBE_PREFIX']+f'/lib:{build_root}/{dependency}/install/lib:'+os.environ.get('LD_LIBRARY_PATH','')
shutdown_delay=float(os.environ.get('NAV2_PROBE_SHUTDOWN_DELAY','2'))
result={'mode':mode,'graceful_manager_shutdown':False,'manager_executable':manager_executable,
        'shutdown_delay_after_detection':shutdown_delay,
        'variant':os.environ.get('NAV2_PROBE_VARIANT','installed')}
rclpy.init(); observer=Node('shutdown_probe')
try:
    ros_prefix='/opt/ros/'+os.environ.get('ROS_DISTRO','jazzy')
    server_executable=os.environ.get('NAV2_PROBE_SERVER',ros_prefix+'/lib/nav2_map_server/map_server')
    server=subprocess.Popen([server_executable,'--ros-args','-p',
        'yaml_filename:='+str(out/'room.yaml')],stdout=log,stderr=log,start_new_session=True)
    children.append(server)
    manager=subprocess.Popen([manager_executable,
        '--ros-args','-r','__node:=probe_manager','-p','node_names:=[map_server]',
        '-p','autostart:=True','-p','bond_timeout:=4.0',
        '-p','use_sim_time:='+('True' if mode=='dead-sim' else 'False')],stdout=log,stderr=log,start_new_session=True,env=manager_env)
    children.append(manager)
    client=observer.create_client(GetState,'/map_server/get_state')
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        if client.wait_for_service(timeout_sec=0.2):
            f=client.call_async(GetState.Request())
            rclpy.spin_until_future_complete(observer,f,timeout_sec=1)
            if f.done() and f.result().current_state.label=='active': break
    else: raise TimeoutError('Map server did not activate')
    deadline=time.monotonic()+10
    while 'Managed nodes are active' not in (out/'process.log').read_text():
        if time.monotonic()>deadline: raise TimeoutError('Manager did not complete bond startup')
        time.sleep(0.1)
    result['bond_startup_confirmed']=True
    result['loaded_nav2_libraries']=sorted(set(line.split()[-1] for line in Path(f'/proc/{manager.pid}/maps').read_text().splitlines() if '/libnav2_' in line))
    time.sleep(2)
    if mode.startswith('dead'):
        server.kill(); server.wait(timeout=3)
        deadline=time.monotonic()+15
        while 'CRITICAL FAILURE' not in (out/'process.log').read_text():
            if time.monotonic()>deadline: raise TimeoutError('Bond loss was not detected; invalid reproduction')
            time.sleep(0.1)
        result['bond_loss_detected']=True
    if mode in ('slow','transition'):
        control=observer.create_client(ManageLifecycleNodes,'/probe_manager/manage_nodes')
        if not control.wait_for_service(timeout_sec=3): raise TimeoutError('Manager control unavailable')
        server.send_signal(signal.SIGSTOP)
        request=ManageLifecycleNodes.Request(); request.command=1
        pause_started=time.monotonic()
        future=control.call_async(request)
        if mode=='transition':
            deadline=time.monotonic()+3
            while 'Deactivating map_server' not in (out/'process.log').read_text():
                if time.monotonic()>deadline: raise TimeoutError('Pause did not reach transition')
                rclpy.spin_once(observer,timeout_sec=0.05)
            result['transition_wait_confirmed']=True
        else:
            time.sleep(3)
            server.send_signal(signal.SIGCONT)
            rclpy.spin_until_future_complete(observer,future,timeout_sec=6)
            result['delayed_pause_seconds']=round(time.monotonic()-pause_started,3)
            result['delayed_pause_succeeded']=future.done() and future.result().success
            if not result['delayed_pause_succeeded']: raise RuntimeError('Delayed pause failed')
    time.sleep(shutdown_delay)
    manager.send_signal(signal.SIGINT)
    started=time.monotonic()
    try:
        manager.wait(timeout=5)
        result['graceful_manager_shutdown']=manager.returncode==0
    except subprocess.TimeoutExpired:
        result['manager_alive_after_5_seconds']=True
        result['shutdown_deadline_seconds']=5
        if '--backtrace' in sys.argv:
            trace=subprocess.run(['gdb','--batch','-ex','set pagination off','-ex','thread apply all bt',
                '-p',str(manager.pid)],capture_output=True,text=True,timeout=15)
            (out/'backtrace.txt').write_text(trace.stdout+trace.stderr)
    result['shutdown_seconds']=round(time.monotonic()-started,3)
except Exception as e: result['error']=str(e)
finally:
    for process in reversed(children):
        if process.poll() is None:
            process.send_signal(signal.SIGCONT)
            process.send_signal(signal.SIGINT)
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
    log.close(); observer.destroy_node(); rclpy.shutdown()
    (out/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True); print(out,flush=True)
sys.exit(0 if result['graceful_manager_shutdown'] else 1)
