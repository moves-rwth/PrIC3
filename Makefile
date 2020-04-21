.PHONY: help lint mypy test docs

VENV_NAME?=env_python
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON=${VENV_NAME}/bin/python3

.DEFAULT: help
help:
	@echo "Available targets: lint, mypy, test, docs"

lint: env_python
	${PYTHON} -m pylint pric3

mypy: env_python
	${PYTHON} -m mypy pric3.py

test: env_python
	${PYTHON} -m pytest --doctest-modules pric3 ${ARGS}

docs: env_python
	$(VENV_ACTIVATE) && cd docs; make html
