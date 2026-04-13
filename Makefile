.PHONY: setup run lint format check test typecheck

setup:
	@command -v uv >/dev/null 2>&1 || { echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
	uv venv .venv
	uv pip install mcp --python .venv

run:
	uv run autoratchet.py

lint:
	uvx ruff check autoratchet.py mcp_server.py

format:
	uvx ruff format autoratchet.py mcp_server.py

test:
	uv run --with pytest --with mcp pytest -v

typecheck:
	ty check --python .venv

check: lint typecheck
	uvx ruff format --check autoratchet.py mcp_server.py
