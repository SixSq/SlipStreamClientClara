# -*- coding: utf-8 -*-
import ast
import re
import sys

from setuptools import find_packages, setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('src/slipstream/cli/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

install_requires = [
    'click',
    'defusedxml',
    'prettytable',
    'urllib3[secure]',
    'requests',
    'six',
]

if sys.version_info < (3, 2):
    install_requires.append('configparser')

setup(
    name='slipstream-cli',
    version=version,
    author="SixSq Sarl",
    author_email='support@sixsq.com',
    url='http://sixsq.com/slipstream',
    description="A tool to useSlipStream.",
    keywords='slipstream devops cli',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    namespace_packages=['slipstream'],
    zip_safe=False,
    license='Apache License, Version 2.0',
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'slipstream=slipstream.cli:main',
        ]
    },
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
