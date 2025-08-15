mypy:
	@echo "Running type checks..."
	@python -m mypy . --follow-untyped-imports --check-untyped-defs

ruff:
	@echo "Running code style checks..."
	@python -m ruff check . --exclude tests --fix

test:
	@echo "Running tests..."
	@TGFS_DATA_DIR=. TGFS_CONFIG_FILE=config-test.yaml pytest

cov:
	@echo "Running tests with coverage..."
	@TGFS_DATA_DIR=. TGFS_CONFIG_FILE=config-test.yaml pytest --cov --cov-report=term-missing

build-push:
	@echo "Building the package..."
	@docker buildx build --platform linux/amd64,linux/arm64 . -t wheatcarrier/tgfs --push
