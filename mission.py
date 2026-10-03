import json
import math
from pathlib import Path
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import ManageLifecycleNodes

out=Path(sys.argv[1]); data={'goals':[], 'lifecycle':[]}
rclpy.init()
node=Node('first_navigation_lesson')
def wait(future, seconds=10):
    deadline=time.monotonic()+seconds
    while not future.done() and time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=0.1)
    if not future.done(): raise TimeoutError('ROS operation timed out')
    return future.result()

try:
    pose_pub=node.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
    def initialize_pose():
        pose=PoseWithCovarianceStamped(); pose.header.frame_id='map'
        pose.header.stamp=node.get_clock().now().to_msg()
        pose.pose.pose.position.x=-2.0; pose.pose.pose.orientation.w=1.0
        pose_pub.publish(pose)
    pose_timer=node.create_timer(0.2,initialize_pose)
    states={name:node.create_client(GetState,f'/{name}/get_state') for name in
            ['map_server','planner_server','controller_server','bt_navigator']}
    deadline=time.monotonic()+90
    active={}
    while time.monotonic()<deadline:
        active={}
        for name,client in states.items():
            if client.service_is_ready():
                future=client.call_async(GetState.Request())
                try:
                    active[name]=wait(future,3).current_state.label
                except TimeoutError:
                    client.remove_pending_request(future)
                    future.cancel()
        if len(active)==len(states) and all(s=='active' for s in active.values()): break
        rclpy.spin_once(node,timeout_sec=0.5)
    else: raise TimeoutError(f'Stack did not activate: {active}')
    pose_timer.cancel()
    data['initial_states']=active
    print('READY:',active,flush=True)
    action=ActionClient(node,NavigateToPose,'/navigate_to_pose')
    if not action.wait_for_server(timeout_sec=10): raise TimeoutError('Navigation action unavailable')
    for x,y in [(-1.0,0.0),(0.0,0.0)]:
        goal=NavigateToPose.Goal(); goal.pose.header.frame_id='map'
        goal.pose.header.stamp=node.get_clock().now().to_msg()
        goal.pose.pose.position.x=x;goal.pose.pose.position.y=y;goal.pose.pose.orientation.w=1.0
        feedback=[]
        def record(msg):
            f=msg.feedback
            feedback.append({'distance_remaining':float(f.distance_remaining),
                'x':float(f.current_pose.pose.position.x),'y':float(f.current_pose.pose.position.y)})
        start=time.monotonic()
        handle=wait(action.send_goal_async(goal,feedback_callback=record))
        if not handle.accepted: raise RuntimeError('Goal rejected')
        response=wait(handle.get_result_async(),50)
        entry={'target':[x,y],'status':response.status,'seconds':time.monotonic()-start,'feedback':feedback}
        data['goals'].append(entry)
        print('GOAL:',[x,y],'status',response.status,flush=True)
        if response.status!=4: raise RuntimeError(f'Goal did not succeed: {response.status}')
    manager=node.create_client(ManageLifecycleNodes,'/lifecycle_manager_navigation/manage_nodes')
    if not manager.wait_for_service(timeout_sec=5): raise TimeoutError('Lifecycle manager unavailable')
    for command,label,expected in [(1,'pause','inactive'),(2,'resume','active')]:
        req=ManageLifecycleNodes.Request();req.command=command
        response=wait(manager.call_async(req),20)
        state=wait(states['controller_server'].call_async(GetState.Request())).current_state.label
        data['lifecycle'].append({'operation':label,'success':response.success,'controller_state':state})
        print(label.upper(),state,flush=True)
        if not response.success or state!=expected: raise RuntimeError(f'Unexpected {label} result')
    data['success']=True
except Exception as exc:
    data['success']=False;data['error']=str(exc)
    print('FAILED:',exc,flush=True)
finally:
    (out/'mission.json').write_text(json.dumps(data,indent=2))
    node.destroy_node();rclpy.shutdown()
sys.exit(0 if data['success'] else 1)
