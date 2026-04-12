.PHONY: setup run lint format check

setup:
	@command -v uv >/dev/null 2>&1 || { echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
	@echo "uv is installed. No other setup needed."

run:
	uv run autoratchet.py

lint:
	uvx ruff check autoratchet.py

format:
	uvx ruff format autoratchet.py

check: lint
	uvx ruff format --check autoratchet.py
