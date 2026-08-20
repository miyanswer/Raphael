import os
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='hirakata_simulation',
            executable='simulator_node',
            name='simulator_node',
            output='screen',
        ),
    ])
