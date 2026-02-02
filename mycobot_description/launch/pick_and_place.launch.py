from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

# MoveIt config builder (standard MoveIt2 pattern)
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    # Build the SAME config MoveIt uses
    moveit_config = (
        MoveItConfigsBuilder("mycobot_280", package_name="cobot_moveit_config")
        .to_moveit_configs()
    )

    # 1) Start move_group (your existing launch)
    move_group_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            get_package_share_directory("cobot_moveit_config"),
            "/launch/move_group.launch.py",
        ])
    )

    # 2) Start your pick_and_place node WITH MoveIt params injected
    pick_place_node = Node(
        package="mycobot_bringup",
        executable="pick_and_place.py",   # must match what ros2 run uses
        name="aruco_pick_place_client",
        output="screen",
        parameters=[
            moveit_config.to_dict(),  
        ],
    )

    return LaunchDescription([
        move_group_launch,
        pick_place_node,
    ])
