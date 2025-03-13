# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="${PATH}:/root/.local/bin"

# Copy pyproject.toml and poetry.lock (if it exists)
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create a virtual environment inside the container
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the project
COPY . .

# Set environment variables
ENV API_DEBUG=False
ENV API_LOG_LEVEL=INFO
ENV API_RATE_LIMIT=100
ENV API_RATE_WINDOW=60

# Create SQLite database directory
RUN mkdir -p /app/api/data

# Make WareHouse directory writable
RUN mkdir -p /app/WareHouse && chmod 777 /app/WareHouse

# Expose the port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]