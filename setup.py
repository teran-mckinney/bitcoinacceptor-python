#!/usr/bin/env python

from setuptools import setup

VERSION = "0.8.0"

DOWNLOAD_URL = (
    "https://go-beyond.org/code/bitcoinacceptor-python/archives/"
    "bitcoinacceptor-python-{VERSION}.tar.gz"
)

setup(
    python_requires=">=3.7",
    name="bitcoinacceptor",
    version=VERSION,
    author="Teran McKinney",
    author_email="sega01@go-beyond.org",
    description="Accept Bitcoin without spending as much Bitcoin",
    keywords=["bitcoin", "bitcoincash", "bitcoinsv", "monero"],
    license="Unlicense",
    url="https://github.com/teran-mckinney/bitcoinacceptor-python/",
    download_url=DOWNLOAD_URL.format(VERSION),
    packages=["bitcoinacceptor"],
    install_requires=[
        "bit",
        "bitcash>=0.5.2.5",
        "bitsv",
        "monero>=0.7.1",
        "requests",
        "sporestack>=1.1.1",
    ],
    tests_require=["black", "flake8", "pytest", "pytest-cov"],
)
