.PHONY: setup run lint format check test typecheck

setup:
	@command -v uv >/dev/null 2>&1 || { echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
	uv venv .venv --allow-existing
	uv pip install mcp pytest --python .venv

run:
	uv run autoratchet.py

lint:
	uvx ruff check .

format:
	uvx ruff format .

test:
	uv run --with pytest --with mcp pytest -v

typecheck:
	uvx ty check --python .venv

check: lint typecheck
	uvx ruff format --check .
