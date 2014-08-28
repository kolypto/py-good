SHELL := /bin/bash

all: build

.PHONY: test test3 check clean build publish install

PATHS=good
TESTS=tests/

# Run tests
NOSEFLAGS?=

test:
	@nosetests  $(NOSEFLAGS) $(TESTS)
test3:
	@nosetests3 $(NOSEFLAGS) $(TESTS)

# Package
check:
	@./setup.py check
clean:
	@rm -rf build/ dist/ *.egg-info/ README.rst
README.md: $(shell find $(PATHS) -type f -name '*.py' -o -name '*.j2') $(wildcard misc/_doc/**)
	@python misc/_doc/README.py | j2 --format=json misc/_doc/README.md.j2 > README.md
README.rst: README.md
	@pandoc -f markdown -t rst -o README.rst README.md
build: README.rst
	@./setup.py build sdist bdist_wheel
publish: README.rst
	@./setup.py build sdist bdist_wheel register upload -r pypi
