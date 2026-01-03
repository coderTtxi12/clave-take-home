# Code Executor Service

Isolated code execution service running in a separate Docker container for security.

## Purpose

This service executes Python code in an isolated environment, preventing malicious code from affecting the main application server.

## Features

- **Isolated execution**: Runs in separate Docker container
- **Resource limits**: CPU and memory limits for safety
- **No persistent storage**: Container is stateless
- **Non-root user**: Runs as unprivileged user

## Usage

The service exposes a single endpoint:

```
POST /execute
Content-Type: application/json

{
  "code": "print('Hello, World!')"
}
```

Response:
```json
{
  "results": ["Hello, World!\n"],
  "errors": []
}
```

## Building

```bash
docker build -t code-executor ./code-executor
```

## Running with Docker Compose

The service is automatically started with:
```bash
docker-compose up code-executor
```

## Health Check

```
GET /health
```

Returns: `{"status": "healthy", "service": "code-executor"}`

