from setuptools import find_packages, setup

package_name = 'jikken'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user25',
    maintainer_email='e1x22044@oit.ac.jp',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'zed_publisher = jikken.zed_publisher:main',
            'zed_publisher_fhd = jikken.zed_publisher_fhd:main',
            'zed_imu_publisher = jikken.zed_imu_publisher:main',
            'conduit_imu_publisher = jikken.conduit_imu_publisher:main',
            'web_imu_publisher = jikken.web_imu_publisher:main',
            'zed_h264_recorder = jikken.zed_h264_recorder_publisher:main',
            'from_h264_to_topic = jikken.from_h264_to_topic:main',
            'zed_svo_recorder = jikken.zed_svo_recorder_publisher:main',
            'svo_publisher = jikken.svo_publisher:main',
        ],
    },
)
