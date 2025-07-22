# Multi-stage Alpine-based Dockerfile for SRE Agent
FROM python:3.11-alpine AS base

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    build-base \
    curl \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base AS development

# Copy test requirements if they exist
COPY requirements-test.txt* ./

# Install test dependencies if file exists
RUN if [ -f requirements-test.txt ]; then \
        pip install --no-cache-dir -r requirements-test.txt; \
    fi

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port for development
EXPOSE 8000

CMD ["python", "-c", "print('Development environment ready.')"]

# Test stage
FROM development AS test

# Set environment variables for testing
ENV PYTHONPATH=/app
ENV AWS_DEFAULT_REGION=us-east-1
ENV AWS_ACCESS_KEY_ID=test
ENV AWS_SECRET_ACCESS_KEY=test

# Run tests by default
CMD ["pytest", "-v", "--cov=src", "--cov-report=html:/app/htmlcov", "--cov-report=term-missing"]

# Production stage (optional, for containerized deployment)
FROM base AS production

# Install only runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    && rm -rf /var/cache/apk/*

# Copy only necessary files
COPY --from=base --chown=appuser:appuser /app /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000')" || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
