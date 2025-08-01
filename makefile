mypy:
	@echo "Running type checks..."
	@python -m mypy . --follow-untyped-imports --check-untyped-defs

ruff:
	@echo "Running code style checks..."
	@python -m ruff check . --exclude tests --fix

build-push:
	@echo "Building the package..."
	@docker buildx build --platform linux/amd64,linux/arm64 . -t wheatcarrier/tgfs --push
