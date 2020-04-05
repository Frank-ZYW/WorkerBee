#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import walk
from os.path import join, isfile, abspath, dirname
from setuptools import find_packages, setup


def read_file(filename):
    with open(filename) as fp:
        return fp.read().strip()


def read_requirements(filename):
    return [line.strip() for line in read_file(filename).splitlines() if not line.startswith('#')]


def get_version():
    about = {}
    with open(join(abspath(dirname(__file__)), 'workerbee', '__version__.py')) as f:
        exec(f.read(), about)
    return about['VERSION']


def package_files(directories):
    paths = []
    for item in directories:
        if isfile(item):
            paths.append(join('..', item))
            continue
        for (path, directories, filenames) in walk(item):
            for filename in filenames:
                paths.append(join('..', path, filename))
    return paths


setup(
    name='workerbee',
    version=get_version(),
    description='Data filter components Based on Scrapy, Scrapy-Redis',
    author='Frank Zhu',
    author_email='Frank_zhu_@outlook.com',
    python_requires='>=3.6.0',
    url='https://github.com/WorkerBee/WorkerBee',
    packages=find_packages(exclude='tests'),
    install_requires=read_requirements('requirements.txt'),
    include_package_data=True,
    license='MIT',
    entry_points={
        'console_scripts': ['workerbee = workerbee.cmd.cmdline:cmd']
    },
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
    package_data={
        '': package_files([
            'workerbee/templates'
        ])
    }
)
