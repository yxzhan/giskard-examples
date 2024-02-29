import os
import psutil
import subprocess
import rospy
from IPython.display import display, IFrame
from sidecar import Sidecar

from giskardpy.python_interface.python_interface import GiskardWrapper
from giskardpy.goals.joint_goals import JointPositionList
from giskardpy.monitors.joint_monitors import JointGoalReached
from geometry_msgs.msg import Twist, PoseStamped, Point, Quaternion, Vector3Stamped, PointStamped, QuaternionStamped
import roslib; roslib.load_manifest('urdfdom_py')
from rqt_joint_trajectory_controller import joint_limits_urdf

# Giskard wrapper instance
gk_wrapper = None

# Directory of the ROS launch files
LAUNCH_FILE_DIR = os.path.abspath(os.path.join(os.getcwd(), "../launch"))
# To display visualization tools on the left
SIDECAR = {
    'rvizweb': None,
    'xpra': None
}
VIS_TOOLS = {
    'rvizweb': True,
    'xpra': False
}
# To manage the roslaunch process in the background
LAUNCH_PROCESS = None
SELECTED_ROBOT = 'pr2_mujoco'
CMD_VEL_TOPIC = '/cmd_vel'
ROBOT_DESCRIPTION = '/robot_description'

# If it is running on binderhub
try:
    JUPYTERHUB_USER = os.environ['JUPYTERHUB_USER']
except KeyError:
    JUPYTERHUB_USER = None

# To fix the resize issue of a iframe
def resizable_iframe(url)
    return HTML(f"""
        <div class="iframe-widget" style="width: calc(100% + 10px);">
            <iframe src="{url}" width="100%", height="100%">
        </div>
    """)

# Open rvizweb
def open_rvizweb():
    if not VIS_TOOLS['rvizweb']:
        return False
    if SIDECAR['rvizweb'] is not None:
        SIDECAR['rvizweb'].close()
    try:
        SIDECAR['rvizweb'] = Sidecar(title='RVIZWEB', anchor='right')
        with SIDECAR['rvizweb']:
            display(resizable_iframe(rospy.get_param('/rvizweb/jupyter_proxy_url')))
    except Exception as e:
        print('Can not fetch rvizweb url.')

# Open XPRA Desktop
def open_xpra():
    if not VIS_TOOLS['xpra']:
        return False
    if SIDECAR['xpra'] is not None:
        return True
    SIDECAR['xpra'] = Sidecar(title='XRPA', anchor='right')
    url_prefix = f"/user/{JUPYTERHUB_USER}" if JUPYTERHUB_USER is not None else ''
    xpra_url = f"{url_prefix}/xprahtml5/index.html"
    with SIDECAR['xpra']:
        display(resizable_iframe(xpra_url))

# Execute the roslaunch command
def _launch_robot(config):
    global LAUNCH_PROCESS
    global CMD_VEL_TOPIC
    global ROBOT_DESCRIPTION
    if LAUNCH_PROCESS is not None:
        LAUNCH_PROCESS.terminate()
        LAUNCH_PROCESS.wait()
    if 'cmd_vel' in config and config['cmd_vel'] is not None: 
        CMD_VEL_TOPIC = config['cmd_vel']
    else:
        CMD_VEL_TOPIC = '/cmd_vel'
    if 'robot_description' in config and config['robot_description'] is not None: 
        ROBOT_DESCRIPTION = config['robot_description']
    else:
        ROBOT_DESCRIPTION = '/robot_description'
        
    launchfile = os.path.join(LAUNCH_FILE_DIR, f"{config['launchfile']}.launch")
    command = [
        'roslaunch',
        launchfile,
        'mujoco_suffix:=' + ('' if VIS_TOOLS['xpra'] else '_headless')
    ]
    open_rvizweb()
    open_xpra()
    print("Executing command:\n" + \
        ' '.join(command) + '\n' + \
        "in the background, the output will be hidden.\n" + \
        "To check the output please execute it in a Terminial!")
    LAUNCH_PROCESS = psutil.Popen(command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)

# moving motion
def move_to(pos, root_link='map', tip_link='base_link'):
    pos_stamp = PointStamped()
    pos_stamp.header.frame_id = root_link
    pos_stamp.point = pos
    gk_wrapper.add_default_end_motion_conditions()
    gk_wrapper.motion_goals.add_cartesian_position(
        root_link=root_link,
        tip_link=tip_link,
        goal_point=pos_stamp,
    )
    gk_wrapper.execute()

# rotation motion
def rotate_robot(ori, root_link='map', tip_link='base_link'):
    ori_stamp = QuaternionStamped()
    ori_stamp.header.frame_id = root_link
    ori_stamp.quaternion = ori
    gk_wrapper.add_default_end_motion_conditions()
    gk_wrapper.motion_goals.add_cartesian_orientation(
        root_link=root_link,
        tip_link=tip_link,
        goal_orientation=ori_stamp,
    )
    gk_wrapper.execute()

# joint position motion
def add_joint_position(joint_goal_list):
    joint_goal = {key: value for d in joint_goal_list for key, value in d.items()}
    gk_wrapper.motion_goals.add_joint_position(goal_state=joint_goal)
    gk_wrapper.add_default_end_motion_conditions()
    gk_wrapper.execute()

# add_cartesian_pose
def add_cartesian_pose(pos, ori, root_link='map', tip_link='base_link'):
    pose_stamp = PoseStamped()
    pose_stamp.header.frame_id = root_link
    pose_stamp.pose.position = pos
    pose_stamp.pose.orientation = ori
    gk_wrapper.add_default_end_motion_conditions()
    gk_wrapper.motion_goals.add_cartesian_pose(
        root_link=root_link,
        tip_link=tip_link,
        goal_pose=pose_stamp,
    )
    gk_wrapper.execute()

# get robot links
def get_links():
    return gk_wrapper.world.get_group_info(gk_wrapper.world.get_group_names()[0]).links

# get all robot links
def get_controlled_joints():
    return gk_wrapper.world.get_controlled_joints(gk_wrapper.world.get_group_names()[0])

# get joint state
def get_joint_state():
    return gk_wrapper.world.get_group_info(gk_wrapper.world.get_group_names()[0]).joint_state


# Functions for blockly
def launch_robot(robot, restart=False):
    global gk_wrapper
    robot = robot.upper()
    robot_dict = {
        'PR2': {
            'name': 'PR2',
            'launchfile': 'pr2_mujoco',
            'cmd_vel': '/pr2/cmd_vel',
            'robot_description': '/pr2/robot_description'
        },
        'HSR': {
            'name': 'HSR',
            'launchfile': 'hsr_mujoco',
            'cmd_vel': '/hsrb4s/cmd_vel',
            'robot_description': '/hsrb4s/robot_description'
        }
    }
    if LAUNCH_PROCESS is not None and not restart:
        print("Robot simulator is already running!")
        return

    if robot in robot_dict:
        _launch_robot(robot_dict[robot])
        rospy.init_node('giskard_playground')
        gk_wrapper = GiskardWrapper()
    else:
        print(f"Robot {robot} is not available!!!")

# Contorl robot base by cmd_vel message
def cmd_vel_move(speed, time):
    cmd_vel_pub = rospy.Publisher(CMD_VEL_TOPIC, Twist, queue_size=100)
    cmd_vel_msg = Twist()
    cmd_vel_msg.linear.x = speed
    cmd_vel_pub.publish(cmd_vel_msg)
    rospy.sleep(time)
    cmd_vel_msg.linear.x = 0
    cmd_vel_pub.publish(cmd_vel_msg)

def cmd_vel_turn(speed, time):
    cmd_vel_pub = rospy.Publisher(CMD_VEL_TOPIC, Twist, queue_size=100)
    cmd_vel_msg = Twist()
    cmd_vel_msg.angular.z = speed
    cmd_vel_pub.publish(cmd_vel_msg)
    rospy.sleep(time)
    cmd_vel_msg.angular.z = 0
    cmd_vel_pub.publish(cmd_vel_msg)
