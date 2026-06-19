.PHONY: install ambient_server playground generate-traces grade

install:
	uv sync

ambient_server:
	uv run python -m expense_agent.fast_api_app

playground:
	uv run adk web .

generate-traces:
	uv run python tests/eval/generate_traces.py

grade:
	agents-cli eval grade --config tests/eval/eval_config.yaml
