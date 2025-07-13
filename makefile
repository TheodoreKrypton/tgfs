mypy:
	@echo "Running type checks..."
	@python -m mypy . --follow-untyped-imports --check-untyped-defs

ruff:
	@echo "Running code style checks..."
	@python -m ruff check . --fix
