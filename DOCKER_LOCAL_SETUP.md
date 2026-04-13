# Local Docker Deployment Guide

This guide explains how to run RAGLens locally using Docker.

## Prerequisites

1. **Docker Desktop** installed and running
   - On macOS: Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)
   - Ensure Docker daemon is running (check Docker Desktop status)

2. **Environment Variables** (optional)
   - Create a `.env` file based on `env.example` if you need custom configuration
   - AWS credentials are optional for local testing (unless using S3/Bedrock features)

## Quick Start

### Option 1: Using the Helper Script (Recommended)

```bash
./run_local_docker.sh
```

This script will:
1. Build the Docker image
2. Start the container
3. Expose the API on port 8080

### Option 2: Using Docker Compose

```bash
docker-compose up --build
```

To run in detached mode:
```bash
docker-compose up -d --build
```

To view logs:
```bash
docker-compose logs -f
```

To stop:
```bash
docker-compose down
```

### Option 3: Manual Docker Commands

1. **Build the image:**
   ```bash
   docker build -t rag-evaluation-api:latest -f Dockerfile .
   ```

2. **Run the container:**
   ```bash
   docker run --rm -it \
     --name rag-evaluation-api \
     -p 8080:8080 \
     -e PYTHONPATH=/app \
     -v "$(pwd)/config:/app/config:ro" \
     rag-evaluation-api:latest
   ```

## API Endpoints

Once the container is running, the API will be available at:

- **Base URL**: http://localhost:8080
- **Health Check**: http://localhost:8080/health
- **API Documentation**: http://localhost:8080/docs (Interactive Swagger UI)
- **API Schema**: http://localhost:8080/openapi.json

## Usage Examples

### Health Check

```bash
curl http://localhost:8080/health
```

### Run Evaluation

```bash
curl -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["What is RAG?"],
    "evaluation_type": "single_turn"
  }'
```

### Multi-turn Evaluation

```bash
curl -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      "What is RAG?",
      "How does it work?",
      "What are the benefits?"
    ],
    "evaluation_type": "multi_turn",
    "session_id": "my-session-123"
  }'
```

## Configuration

The application uses configuration from `config/config.yaml`. The Docker container mounts this directory as read-only, so you can modify the config without rebuilding.

Environment variables can override YAML settings. See `env.example` for available options.

## Troubleshooting

### Docker daemon not running

If you see: `Cannot connect to the Docker daemon`

- **macOS**: Open Docker Desktop application
- **Linux**: Start Docker service: `sudo systemctl start docker`

### Port already in use

If port 8080 is already in use:

1. Change the port in `docker-compose.yml`:
   ```yaml
   ports:
     - "8081:8080"  # Change 8081 to any available port
   ```

2. Or specify a different port when running:
   ```bash
   docker run -p 8081:8080 rag-evaluation-api:latest
   ```

### Container fails to start

Check the logs:
```bash
docker logs rag-evaluation-api
```

Or with docker-compose:
```bash
docker-compose logs
```

### AWS Credentials Required

If you're using S3 or Bedrock features, you need to provide AWS credentials:

1. **Via environment variables:**
   ```bash
   docker run -p 8080:8080 \
     -e AWS_ACCESS_KEY_ID=your_key \
     -e AWS_SECRET_ACCESS_KEY=your_secret \
     rag-evaluation-api:latest
   ```

2. **Via AWS credentials file:**
   ```bash
   docker run -p 8080:8080 \
     -v ~/.aws:/root/.aws:ro \
     rag-evaluation-api:latest
   ```

## Development

To make code changes and test:

1. Make your changes
2. Rebuild the image: `docker build -t rag-evaluation-api:latest -f Dockerfile .`
3. Restart the container

For faster iteration during development, you can mount the code directory:

```bash
docker run --rm -it \
  -p 8080:8080 \
  -v "$(pwd):/app" \
  rag-evaluation-api:latest
```

**Note**: This requires the dependencies to be installed in your local environment or a volume mount.

## Stopping the Container

- If running with the script: Press `Ctrl+C`
- If running with docker-compose: `docker-compose down`
- If running manually: `docker stop rag-evaluation-api` or `Ctrl+C`

