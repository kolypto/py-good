#!/usr/bin/env python
""" Slim validation yet handsome validation library (voluptuous 2) """

from setuptools import setup, find_packages

setup(
    # http://pythonhosted.org/setuptools/setuptools.html
    name='good',
    version='0.0.3-2',
    author='Mark Vartanyan',
    author_email='kolypto@gmail.com',

    url='https://github.com/kolypto/py-good',
    license='BSD',
    description=__doc__,
    long_description=open('README.rst').read(),
    keywords=['validation'],

    packages=find_packages(),
    scripts=[],
    entry_points={},

    install_requires=[
        'six >= 1.7.3',
    ],
    extras_require={
        '_dev': ['wheel', 'nose', 'exdoc', 'jinja2', 'j2cli'],
    },
    include_package_data=True,
    test_suite='nose.collector',

    platforms='any',
    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
