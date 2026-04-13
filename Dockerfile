FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including git for langchain-community)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install OpenTelemetry for observability (required for Agent Core)
RUN pip install --no-cache-dir aws-opentelemetry-distro>=0.10.1

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV GIT_PYTHON_REFRESH=quiet

# Expose ports (Agent Core uses port 9000, but we expose multiple for compatibility)
EXPOSE 9000 8000 8080

# Entry point for Bedrock Agent Core Runtime
# Run as HTTP server on port 9000 (Agent Core default)
CMD ["opentelemetry-instrument", "python", "-m", "uvicorn", "agentcore_entry:app", "--host", "0.0.0.0", "--port", "9000"]
