.PHONY: install ambient_server playground

install:
	uv sync

ambient_server:
	uv run python -m expense_agent.fast_api_app

playground:
	uv run adk web .
