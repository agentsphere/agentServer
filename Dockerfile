# Stage 1: Base image with Python and environment setup
FROM python:3.12-slim-bookworm AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    VENV_PATH="/opt/venv"

# Update PATH
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
#RUN curl -sSL https://install.python-poetry.org | python3 - \
#    && poetry --version

RUN pip install uv uvicorn

# Upgrade pip
RUN pip install --upgrade pip

# Stage 2: Install dependencies
FROM base AS builder

# Set working directory
WORKDIR /app

# Copy pyproject.toml and poetry.lock
COPY pyproject.toml uv.lock ./


# Install dependencies
RUN uv sync --no-dev 


# Stage 3: Final image
FROM base AS final

# Set working directory
WORKDIR /app
ENV PATH=".venv/bin:$PATH"

# Copy installed dependencies from builder stage
COPY --from=builder /app/.venv .venv

# Copy application code
COPY main.py .

ENV PORT=8000
# Expose the port
EXPOSE 8000
#RUN uvicorn
# Command to run the application
CMD ["/bin/sh", "-c", "uvicorn main:app --host 0.0.0.0"]
# Use official Python image

