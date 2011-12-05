#!/usr/bin/env python

from distutils.core import setup

setup(name='reconstructor',
    version = '4.0',
    author = 'Lumentica',
    author_email = 'info@lumentica.com',
    packages = ['reconstructor'],
    description = 'GNU/Linux distribution creator',
    license = 'License :: OSI Approved :: GNU General Public License (GPL)',
    long_description = """ 
    GNU/Linux distribution creator""",
    #install_requires = [''],
    platforms = [ 
        "All",
        ],  
    classifiers = [ 
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
        ]   
    )   


