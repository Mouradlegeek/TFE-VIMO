"""
Launch file complet VIMO — TFE ISIB 2025-2026
Lance tous les noeuds du pipeline en une commande :
  ros2 launch vimo_pkg vimo_full.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([

        Node(
            package='vimo_pkg',
            executable='rpm_bridge_node',
            name='rpm_bridge_node',
            output='screen',
            emulate_tty=True,
        ),

        Node(
            package='vimo_pkg',
            executable='ekf_node',
            name='ekf_node',
            output='screen',
            emulate_tty=True,
        ),

        Node(
            package='vimo_pkg',
            executable='vimo_sync_node',
            name='vimo_sync_node',
            output='screen',
            emulate_tty=True,
        ),

        Node(
            package='vimo_pkg',
            executable='safety_monitor',
            name='safety_monitor',
            output='screen',
            emulate_tty=True,
        ),

        Node(
            package='vimo_pkg',
            executable='oakd_node',
            name='oakd_node',
            output='screen',
            emulate_tty=True,
        ),

        Node(
            package='vimo_pkg',
            executable='dualsense_bridge',
            name='dualsense_bridge',
            output='screen',
            emulate_tty=True,
        ),

        Node(
            package='vimo_pkg',
            executable='joy_to_px4',
            name='joy_to_px4',
            output='screen',
            emulate_tty=True,
        ),

        Node(
            package='vimo_pkg',
            executable='dataset_recorder',
            name='dataset_recorder',
            output='screen',
            emulate_tty=True,
        ),
    ])
