# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup(
    name='slipstream-cli',
    version='0.1.0',
    author="Sebastien Fievet",
    author_email='sebastien@sixsq.com',
    url='https://github.com/slipstream/slipstream-cli',
    description="A SlipStream's companion tool for command line lovers.",
    package_dir={'': 'src'},
    packages=find_packages('src'),
    namespace_packages=['slipstream'],
    zip_safe=False,
    license='Apache License, Version 2.0',
    include_package_data=True,
    install_requires=[
        'click',
        'defusedxml',
        'prettytable',
        'requests',
        'six',
    ],
    entry_points='''
    [console_scripts]
    slipstream=slipstream.cli:main
    ''',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development'
    ],
)
