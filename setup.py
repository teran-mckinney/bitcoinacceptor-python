#!/usr/bin/env python

from setuptools import setup

VERSION = '0.3.2'

DOWNLOAD_URL = 'https://github.com/teran-mckinney/bitcoinacceptor-python/tarball/{}'

setup(
    python_requires='>=3.3',
    name='bitcoinacceptor',
    version=VERSION,
    author='Teran McKinney',
    author_email='sega01@go-beyond.org',
    description='Accept Bitcoin without spending as much Bitcoin',
    keywords=['bitcoin', 'bitcoincash', 'bitcoinsv'],
    license='Unlicense',
    url='https://github.com/teran-mckinney/bitcoinacceptor-python/',
    download_url=DOWNLOAD_URL.format(VERSION),
    packages=['bitcoinacceptor'],
    install_requires=[
        'requests',
        'bit',
        'bitcash>=0.5.2.5',
        'bitsv'
    ],
    tests_require=['flake8', 'pytest']
)
