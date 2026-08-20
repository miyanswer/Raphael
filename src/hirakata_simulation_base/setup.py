from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'hirakata_simulation'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user25',
    maintainer_email='user25@example.com',
    description='3D Vision Simulation Environment for Hirakata AGV Course',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'simulator_node = hirakata_simulation.simulator_node:main',
            'vision_control_node = hirakata_simulation.vision_control_node:main',
        ],
    },
)
