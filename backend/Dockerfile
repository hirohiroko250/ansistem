# OZA System Backend Dockerfile
FROM python:3.11-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app

# Set work directory
WORKDIR $APP_HOME

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/ requirements/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements/production.txt

# Copy project
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser $APP_HOME
USER appuser

# Collect static files
RUN python manage.py collectstatic --noinput --settings=config.settings.production || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run daphne (ASGI server with WebSocket support)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
