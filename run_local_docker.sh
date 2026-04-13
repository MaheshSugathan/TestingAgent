#!/bin/bash

# Script to build and run the RAG Evaluation API locally in Docker

set -e

echo "🐳 Building Docker image..."
docker build -t rag-evaluation-api:latest -f Dockerfile .

echo ""
echo "✅ Build complete!"
echo ""
echo "🚀 Starting container..."
echo ""
echo "The API will be available at: http://localhost:8080"
echo "Health check: http://localhost:8080/health"
echo "API docs: http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to stop the container"
echo ""

# Run the container
docker run --rm -it \
  --name rag-evaluation-api \
  -p 8080:8080 \
  -e PYTHONPATH=/app \
  -e PYTHONUNBUFFERED=1 \
  -v "$(pwd)/config:/app/config:ro" \
  rag-evaluation-api:latest

