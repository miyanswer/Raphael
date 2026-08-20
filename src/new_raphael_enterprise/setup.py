from setuptools import find_packages, setup

package_name = 'new_raphael_enterprise'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user25',
    maintainer_email='user25@example.com',
    description='Raphael Enterprise Multi-Agent Development Platform',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'interpreter_pm = new_raphael_enterprise.interpreter_pm:main',
            'architect_cto = new_raphael_enterprise.architect_cto:main',
            'coder_agent = new_raphael_enterprise.coder_agent:main',
            'qa_agent = new_raphael_enterprise.qa_agent:main',
            'memory_manager = new_raphael_enterprise.memory_manager:main',
            'orchestrator = new_raphael_enterprise.orchestrator:main',
        ],
    },
)
