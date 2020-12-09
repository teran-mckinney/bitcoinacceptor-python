#!/bin/sh

set -e

black --check .
flake8
pytest -vx --cov=bitcoinacceptor --cov-fail-under=80 --cov-report term-missing

echo Success
