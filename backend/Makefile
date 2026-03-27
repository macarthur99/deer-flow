install:
	python -m pip install -r requirements-dev.txt

dev:
	uv run langgraph dev --no-browser --allow-blocking --no-reload

gateway:
	PYTHONPATH=. python -m uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001

test:
	PYTHONPATH=. python -m pytest tests/ -v

lint:
	uvx ruff check .

format:
	uvx ruff check . --fix && uvx ruff format .
