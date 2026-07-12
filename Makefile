PYTHON ?= python
PORT ?= 8000

export PYTHONPATH := backend

-include .env
export

.PHONY: install dev test build run

install:
	$(PYTHON) -m pip install -r backend/requirements.txt

dev:
	$(PYTHON) -m uvicorn app.main:app --reload --reload-dir backend --port $(PORT)

run:
	$(PYTHON) -m uvicorn app.main:app --port $(PORT)

test:
	$(PYTHON) -m pytest backend/tests

build:
	$(PYTHON) -m compileall backend/app
	npm --prefix frontend ci || npm --prefix frontend install
	npm --prefix frontend run build
