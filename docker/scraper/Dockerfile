FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QT_X11_NO_MITSHM=1

# Install setuptools<71 (required by playwright-stealth's pkg_resources import)
# setuptools>=71 removed pkg_resources as top-level module
RUN pip install --no-cache-dir "setuptools<71"

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1
RUN poetry config virtualenvs.create false

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry lock --no-update --no-interaction 2>/dev/null || true && \
    poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Install package
RUN poetry install --no-interaction --no-ansi

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
