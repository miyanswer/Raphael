from setuptools import find_packages, setup

package_name = 'raphael_enterprise'

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
            'cto_node = raphael_enterprise.cto_node:main',
            'architect_node = raphael_enterprise.architect_node:main',
            'reviewer_node = raphael_enterprise.reviewer_node:main',
            'course_lap_node = raphael_enterprise.course_lap_node:main',
        ],
    },
)
