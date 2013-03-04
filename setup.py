#!/usr/bin/env python
import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = '0.1.0'
requires = open('requirements.txt', 'r').read().splitlines()

setup(
    name='reconstructor',
    version=version,
    description='GNU/Linux distribution toolkit',
    url='http://github.com/ehazlett/reconstructor.engine',
    download_url=('https://github.com/ehazlett/'
        'reconstructor.engine/archive/%s.tar.gz' % version),
    author='Evan Hazlett',
    author_email='ejhazlett@gmail.com',
    keywords=['linux', 'reconstructor'],
    license='Apache Software License 2.0',
    packages=['arcus'],
    install_requires=requires,
    test_suite='tests.all_tests',
    entry_points={
        'console_scripts': [
            'reconstructot = reconstructor.runner:main',
        ],
    },
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        ]
)
