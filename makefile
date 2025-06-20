type-check:
	@echo "Running type checks..."
	@python -m mypy . --follow-untyped-imports