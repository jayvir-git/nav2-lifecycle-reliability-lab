"""Kill only this lesson's controller after observed motion; observe for 20 s."""
import json
import os
from pathlib import Path
import signal
import sys
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose

out, launch_group = Path(sys.argv[1]), int(sys.argv[2])
data = {'success': False, 'events': [], 'odometry': [], 'state_samples': [],
        'observation_window_seconds': 20, 'fault': 'SIGKILL controller process',
        'prediction': 'Loss of controller bond should trigger coordinated lifecycle teardown. Action outcome and simulated motion must be measured.'}
rclpy.init()
node = Node('controller_failure_observer')
start = time.monotonic()
def stamp(): return round(time.monotonic()-start, 3)
def event(kind, **fields):
    item = {'seconds': stamp(), 'event': kind, **fields}
    data['events'].append(item)
    print(item, flush=True)
def wait(future, seconds=10):
    deadline = time.monotonic()+seconds
    while not future.done() and time.monotonic()<deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
    if not future.done(): raise TimeoutError('ROS operation timed out')
    return future.result()
def record_odom(msg):
    if not data['odometry'] or stamp()-data['odometry'][-1]['seconds'] >= 0.1:
        data['odometry'].append({'seconds': stamp(), 'x': msg.pose.pose.position.x,
            'y': msg.pose.pose.position.y, 'vx': msg.twist.twist.linear.x})
sub = node.create_subscription(Odometry, '/odom', record_odom, 10)
try:
    pub = node.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
    def initialize_pose():
        pose = PoseWithCovarianceStamped(); pose.header.frame_id = 'map'
        pose.header.stamp = node.get_clock().now().to_msg()
        pose.pose.pose.position.x = -2.0; pose.pose.pose.orientation.w = 1.0
        pub.publish(pose)
    pose_timer = node.create_timer(0.2, initialize_pose)
    clients = {name: node.create_client(GetState, '/'+name+'/get_state') for name in
               ['map_server', 'planner_server', 'controller_server', 'bt_navigator']}
    deadline = time.monotonic()+90
    while time.monotonic()<deadline:
        states = {}
        for name,c in clients.items():
            if c.service_is_ready():
                future = c.call_async(GetState.Request())
                try:
                    states[name] = wait(future,3).current_state.label
                except TimeoutError:
                    c.remove_pending_request(future)
                    future.cancel()
        if len(states)==4 and all(v=='active' for v in states.values()): break
        rclpy.spin_once(node, timeout_sec=0.2)
    else: raise TimeoutError('Stack not ready: '+str(states))
    pose_timer.cancel()
    event('ready', states=states)
    # Verify executable, UID and process group before targeting any PID.
    candidates = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            argv = (p/'cmdline').read_bytes().split(b'\0')
            if argv[0] == b'/opt/ros/jazzy/lib/nav2_controller/controller_server' and os.getpgid(int(p.name))==launch_group and p.stat().st_uid==os.getuid():
                candidates.append(int(p.name))
        except (OSError, ProcessLookupError): pass
    if len(candidates)!=1: raise RuntimeError('Expected exactly one owned controller: '+str(candidates))
    pid = candidates[0]
    action = ActionClient(node, NavigateToPose, '/navigate_to_pose')
    if not action.wait_for_server(timeout_sec=10): raise TimeoutError('Action unavailable')
    goal = NavigateToPose.Goal(); goal.pose.header.frame_id='map'
    goal.pose.header.stamp=node.get_clock().now().to_msg()
    goal.pose.pose.position.x=2.0; goal.pose.pose.orientation.w=1.0
    feedback=[]
    def record(msg): feedback.append(msg.feedback.current_pose.pose.position.x)
    handle=wait(action.send_goal_async(goal, feedback_callback=record))
    if not handle.accepted: raise RuntimeError('Goal rejected')
    event('goal_accepted', target=[2,0])
    result_future=handle.get_result_async()
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
        if feedback and feedback[-1]>-1.85: break
        if result_future.done(): raise RuntimeError('Goal ended before fault')
    else: raise TimeoutError('No observed movement before fault')
    if os.getpgid(pid)!=launch_group: raise RuntimeError('Controller process group changed')
    os.kill(pid, signal.SIGKILL)
    event('controller_killed', pid=pid, x=feedback[-1])
    deadline=time.monotonic()+20
    pending={}; next_query=0; action_recorded=False
    while time.monotonic()<deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
        if result_future.done() and not action_recorded:
            response=result_future.result()
            event('action_terminal', status=response.status)
            data['action_status']=response.status; action_recorded=True
        for name,(future,sent) in list(pending.items()):
            if future.done():
                data['state_samples'].append({'seconds':stamp(),'node':name,'state':future.result().current_state.label})
                del pending[name]
            elif time.monotonic()-sent>1:
                clients[name].remove_pending_request(future)
                data['state_samples'].append({'seconds':stamp(),'node':name,'state':'no_response_within_1s'})
                del pending[name]
        if time.monotonic()>=next_query:
            for name,c in clients.items():
                if name not in pending: pending[name]=(c.call_async(GetState.Request()),time.monotonic())
            next_query=time.monotonic()+1
    if not action_recorded:
        data['action_status']=None
        event('action_pending_at_observation_end')
    event('observation_complete')
    data['success']=True
except Exception as exc:
    data['error']=str(exc); event('experiment_error', message=str(exc))
finally:
    (out/'mission.json').write_text(json.dumps(data,indent=2))
    node.destroy_node(); rclpy.shutdown()
sys.exit(0 if data['success'] else 1)
