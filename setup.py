# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE.txt') as f:
    license = f.read()

with open('requirements.txt') as f:
    requires = f.read()

with open('test-requirements.txt') as f:
    test_requires = f.read()

setup(
    name='crop',
    version='0.1.0',
    description='Cataloged Repeatable Operations Packages',
    long_description=readme,
    author='Ryan Scott Brown',
    author_email='ryan@serverlesscode.com',
    url='https://github.com/ryansb/crop',
    install_requires=requires.split('\n'),
    tests_require=test_requires.split('\n'),
    scripts=['bin/crop'],
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
