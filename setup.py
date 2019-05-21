#!/usr/bin/env python

import setuptools

CLASSIFIERS = """\
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
License :: OSI Approved :: BSD License
Programming Language :: Python
Programming Language :: Python :: 3.7
Topic :: Software Development
"""

setuptools.setup(
    name='mp_manager',
    description='Simple python multiprocessing manager',
    long_description=open('README.rst').read(),
    version='0.1',
    author='Dmitriy Pomazunovskiy',
    author_email='forestwheel@gmail.com',
    classifiers=[_f for _f in CLASSIFIERS.split('\n') if _f],
    url='http://pypi.python.org/pypi/mp_manager',
    license='BSD',
    setup_requires=['wheel'],
    packages=['mp_manager']
)
