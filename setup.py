from setuptools import setup

setup (
    name='ec2mgr',
    version='0.1',
    author="Enyou Li",
    author_email="enyou_li@yahoo.com",
    description="EC2-Manager is a trail software for managing EC2 instances",
    license="GPLv3+",
    packages=['ec2mgr'],
    url="https://github.com/frank-python65/ec2-manager.git",
    install_requires=[
        'click',
        'boto3'
    ],
    entry_points='''
        [console_scripts]
        ec2mgr=ec2mgr.ec2mgr:cli
    ''',
)
