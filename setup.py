from setuptools import find_packages, setup

setup(
    name='PrIC3',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pric3 = pric3.cmd:main',
        ],
    },
)
