SHELL := /bin/bash

all: build

# Tools
.PHONY: profile
profile:
	@python -m cProfile -o profile.out `which nosetests`

# Generation
README.md: $(shell find * -type f -name '*.py' -o -name '*.j2') $(wildcard misc/_doc/**)
	@python misc/_doc/README.py | j2 --format=json misc/_doc/README.md.j2 > README.md
README.rst: README.md
	@pandoc -f markdown -t rst -o README.rst README.md

# Package
.PHONY: clean build publish
clean:
	@rm -rf build/ dist/ *.egg-info/ README.rst
build: README.rst
	@./setup.py build sdist bdist_wheel
publish: README.rst
	@./setup.py build sdist bdist_wheel register upload -r pypi
