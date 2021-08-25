# See https://tech.davis-hansson.com/p/make/
SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

ifeq ($(origin .RECIPEPREFIX), undefined)
  $(error This Make does not support .RECIPEPREFIX. Please use GNU Make 4.0 or later)
endif
.RECIPEPREFIX = >

##############################################

PYTHON_VERSION = python3.9
VENV_NAME := venv
VENV_BIN := $(VENV_NAME)/bin
ACTIVATE = $(VENV_BIN)/activate
PYTHON = $(VENV_BIN)/python3

$(PYTHON):
> test -d $(VENV_NAME) || $(PYTHON_VERSION) -m venv $(VENV_NAME)
> $(PYTHON) -m pip install -U pip

venv: $(PYTHON)

install: venv requirements.txt setup.py
> $(PYTHON) -m pip install -r requirements.txt
> $(VENV_BIN)/pre-commit install

lint:
> $(PYTHON) -m flake8 --count --show-source --statistics camera_alignment_core
.PHONY: lint

type-check:
> $(PYTHON) -m mypy --ignore-missing-imports camera_alignment_core
.PHONY: type-check

fmt:
> $(PYTHON) -m black camera_alignment_core
.PHONY: fmt

fmt-check:
> $(PYTHON) -m black --check camera_alignment_core
.PHONY: fmt

import-sort:
> $(PYTHON) -m isort camera_alignment_core
.PHONY: import-sort

import-sort-check:
> $(PYTHON) -m isort --check --diff camera_alignment_core
.PHONY: import-sort

test:
> $(PYTHON) -m pytest camera_alignment_core/tests/
.PHONY: test

test-exclude-slow:
> $(PYTHON) -m pytest -m "not slow"
.PHONY: test-exclude-slow

clean:  # Clear proj dir of all .gitignored files
> git clean -xfd -e .vscode
.PHONY: clean

docs:
> source $(ACTIVATE) && sphinx-apidoc -f -o docs camera_alignment_core camera_alignment_core/tests
> source $(ACTIVATE) && sphinx-build -b html docs docs/build
.PHONY: docs

build: clean install
> $(PYTHON) setup.py bdist_wheel
.PHONY: build

publish: build
> $(PYTHON) -m twine upload --verbose -r release-local --cert /etc/ssl/certs/aics-ca.pem dist/*.whl
.PHONY: publish

publish-snapshot: build
> $(PYTHON) -m twine upload --verbose -r snapshot-local --cert /etc/ssl/certs/aics-ca.pem dist/*.whl
.PHONY: publish-snapshot

bumpversion-release:
> $(PYTHON) -m bumpversion --list release
.PHONY: bumpversion-release

bumpversion-major:
> $(PYTHON) -m bumpversion --list major
.PHONY: bumpversion-major

bumpversion-minor:
> $(PYTHON) -m bumpversion --list minor
.PHONY: bumpversion-minor

bumpversion-patch:
> $(PYTHON) -m bumpversion --list patch
.PHONY: bumpversion-patch

bumpversion-dev:
> $(PYTHON) -m bumpversion --list devbuild
.PHONY: bumpversion-dev
