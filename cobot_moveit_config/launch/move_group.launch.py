from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch

from launch import LaunchDescription
from launch_ros.actions import SetParameter


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("mycobot_280", package_name="cobot_moveit_config")
        .to_moveit_configs()
    )

    move_group_launch = generate_move_group_launch(moveit_config)

    return LaunchDescription([
        # IMPORTANT: make MoveIt use Gazebo clock
        SetParameter(name="use_sim_time", value=True),

        # include original move_group launch actions
        *move_group_launch.entities
    ])
