# Docker Setup Guide for Chat Service

This guide explains how to run the Chat Service using Docker with PostgreSQL.

## Prerequisites

- Docker installed on your machine
- Docker Compose installed on your machine
- A `.env` file with your `OPENROUTER_API_KEY` (see `.env.example`)

## Quick Start

### 1. Set Up Environment Variables

Create a `.env` file in the project root directory (or copy from `.env.example`):

```bash
cp .env.example .env
```

Then edit `.env` and add your `OPENROUTER_API_KEY`:

```env
OPENROUTER_API_KEY=your_actual_api_key_here
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/chatdb
SUMMARIZATION_MODEL=openai/gpt-3.5-turbo
DEFAULT_LLM_1=google/gemini-pro
DEFAULT_LLM_2=mistralai/mistral-7b-instruct
```

### 2. Build and Run with Docker Compose

Run everything with a single command:

```bash
docker-compose up --build
```

This command will:

- Build the FastAPI application image
- Start PostgreSQL with pgvector extension
- Initialize the database
- Start the FastAPI application on `http://localhost:8000`

### 3. Access the Application

- **FastAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Base URL**: http://localhost:8000

## Docker Compose Services

### PostgreSQL Service

- **Container Name**: `chat-service-postgres`
- **Host Port**: `5432`
- **Database**: `chatdb`
- **Username**: `postgres`
- **Password**: `postgres`
- **Image**: `ankane/pgvector:latest` (includes pgvector extension)

### FastAPI Application Service

- **Container Name**: `chat-service-app`
- **Host Port**: `8000`
- **Auto-reload**: Enabled (watches for file changes)
- **Environment**: Connected to PostgreSQL service

## Common Commands

### Run in the background

```bash
docker-compose up -d
```

### View logs

```bash
docker-compose logs -f app
docker-compose logs -f postgres
```

### Stop services

```bash
docker-compose down
```

### Stop and remove data

```bash
docker-compose down -v
```

### Rebuild without cache

```bash
docker-compose up --build --no-cache
```

### Access PostgreSQL shell

```bash
docker-compose exec postgres psql -U postgres -d chatdb
```

## Troubleshooting

### Port Already in Use

If port 8000 or 5432 is already in use, modify the ports in `docker-compose.yml`:

```yaml
services:
  postgres:
    ports:
      - "5433:5432" # Change from 5432 to 5433
  app:
    ports:
      - "8001:8000" # Change from 8000 to 8001
```

### Database Connection Issues

Ensure PostgreSQL is healthy before the app starts by checking the health check status:

```bash
docker-compose ps
```

Look for `postgres` service to have `(healthy)` status.

### Missing API Key

If you see authentication errors, verify that `OPENROUTER_API_KEY` is properly set in your `.env` file:

```bash
cat .env | grep OPENROUTER_API_KEY
```

## Building the Docker Image Manually

If you want to build the image separately:

```bash
docker build -t chat-service:latest .
```

## Running Without Docker Compose

To run only the FastAPI app (requiring PostgreSQL to be running locally):

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://postgres:postgres@localhost:5432/chatdb" \
  -e OPENROUTER_API_KEY="your_key_here" \
  chat-service:latest
```
