#!/usr/bin/env python
""" Slim yet handsome validation library """

from setuptools import setup, find_packages

setup(
    # http://pythonhosted.org/setuptools/setuptools.html
    name='good',
    version='0.0.7-1',
    author='Mark Vartanyan',
    author_email='kolypto@gmail.com',

    url='https://github.com/kolypto/py-good',
    license='BSD',
    description=__doc__,
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    keywords=['validation'],

    packages=find_packages(),
    scripts=[],
    entry_points={},

    install_requires=[
        'six >= 1.7.3',
    ],
    extras_require={
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
