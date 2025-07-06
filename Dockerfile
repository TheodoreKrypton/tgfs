FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry to install in system
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --only=main --no-root

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY tgfs/ ./tgfs/
COPY asgidav/ ./asgidav/
COPY main.py ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash tgfs
USER tgfs

# Expose WebDAV port
EXPOSE 1900

# Run the application
CMD ["python", "main.py"]