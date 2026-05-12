# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DISABLE_DB=true

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 user

# Create logs directory with proper ownership
RUN mkdir -p logs && chown -R user:user logs

# Create placeholder files for Gmail credentials (will be replaced via web upload)
RUN touch credentials.json token.json && chown user:user credentials.json token.json

# Copy requirements first for better caching
COPY --chown=user:user requirements.txt .

# Switch to non-root user
USER user

# Set user environment variables
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH

# Install Python dependencies as user
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY --chown=user:user app/ ./app/

# Expose port
EXPOSE 7860

# Run FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
