from setuptools import setup

package_name = 'vimo_pkg'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         [f'{package_name}/resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch',
         [f'{package_name}/launch/vimo_full.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Mourad AARAB',
    maintainer_email='aarab.mourad2002@gmail.com',
    description='VIMO ROS2 nodes — TFE ISIB 2025-2026',
    license='MIT',
    entry_points={
        'console_scripts': [
            'rpm_bridge_node  = vimo_pkg.rpm_bridge_node:main',
            'ekf_node         = vimo_pkg.ekf_node:main',
            'vimo_sync_node   = vimo_pkg.vimo_sync_node:main',
            'safety_monitor   = vimo_pkg.safety_monitor:main',
            'dualsense_bridge = vimo_pkg.dualsense_bridge:main',
            'oakd_node        = vimo_pkg.oakd_node:main',
            'dataset_recorder = vimo_pkg.dataset_recorder:main',
            'joy_to_px4       = vimo_pkg.joy_to_px4:main',
        ],
    },
)
