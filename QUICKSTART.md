# Quick Start Guide

## 5-Minute Setup

### Step 1: Install Dependencies

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
source venv/bin/activate  # On macOS/Linux

pip install -r requirements.txt
```

### Step 2: Set Up PostgreSQL

```bash
# Create database (local PostgreSQL) or use Docker Compose (recommended)
# Option A: Local PostgreSQL
# Create the database
psql -U postgres -c "CREATE DATABASE chatdb;"

# Connect and install pgvector
psql -U postgres -d chatdb -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Option B: Run PostgreSQL with Docker Compose (includes pgvector)
docker-compose up -d

# The Compose setup uses an image with pgvector and an init script that
# creates the `vector` extension in `chatdb` on first start.
```

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```
DATABASE_URL=postgresql://postgres:your_password@localhost/chatdb
OPENROUTER_API_KEY=your_key_here
SUMMARIZATION_MODEL=upstage/solar-pro-3:free
DEFAULT_LLM_1=google/gemini-pro
DEFAULT_LLM_2=mistralai/mistral-7b-instruct
```

### Step 4: Run the Server

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API docs.

## Example API Usage

### Create a Thread

```bash
curl -X POST "http://localhost:8000/threads/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Support Chat",
    "system_prompt": "You are a helpful support agent."
  }'
```

### Send a Message

```bash
curl -X POST "http://localhost:8000/threads/1/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "user123",
    "content": "How do I reset my password?",
    "model": "google/gemini-pro"
  }'
```

### View Thread History

```bash
curl "http://localhost:8000/threads/1"
```

## Project Structure at a Glance

| Folder      | Purpose                                         |
| ----------- | ----------------------------------------------- |
| `api/`      | FastAPI routes and endpoints                    |
| `core/`     | Configuration settings                          |
| `crud/`     | Database queries (CREATE, READ, UPDATE, DELETE) |
| `db/`       | Database models and connection setup            |
| `schemas/`  | Request/response validation schemas             |
| `services/` | Business logic (LLM, summarization, threading)  |

## Key Files Explained

- **main.py**: FastAPI app entry point
- **models.py**: Database table definitions
- **llm_service.py**: OpenRouter API integration
- **thread_service.py**: Message processing logic
- **routes.py**: API endpoint definitions

## Next Steps

1. Review API documentation: `http://localhost:8000/docs`
2. Test endpoints with example payloads
3. Configure different LLM models as needed
4. Deploy with Docker or traditional hosting
5. Add authentication/authorization for production

## Troubleshooting Quick Fixes

| Issue                        | Solution                                                 |
| ---------------------------- | -------------------------------------------------------- |
| "No such table: threads"     | Run `uvicorn app.main:app --reload` once to init tables  |
| "Cannot connect to database" | Verify PostgreSQL is running and DATABASE_URL is correct |
| "Invalid API key"            | Check OpenRouter key at https://openrouter.ai/keys       |
| "pgvector not found"         | Run `psql -d chatdb -c "CREATE EXTENSION vector"`        |
| "Docker Compose"             | Run `docker-compose up -d` to start PostgreSQL locally   |

## What This Service Does

1. **Manages Chat Threads**: Create persistent chat contexts with system prompts
2. **Integrates LLMs**: Connect to multiple AI models via OpenRouter
3. **Maintains History**: Store all messages with timestamps and model info
4. **Summarizes Automatically**: Compress conversation history every 10 messages
5. **Provides REST API**: Clean endpoints for thread and message management

## Environment Variables Reference

| Variable              | Purpose                      |
| --------------------- | ---------------------------- |
| `DATABASE_URL`        | PostgreSQL connection string |
| `OPENROUTER_API_KEY`  | Your OpenRouter API key      |
| `SUMMARIZATION_MODEL` | Model for creating summaries |
| `DEFAULT_LLM_1`       | Primary LLM model option     |
| `DEFAULT_LLM_2`       | Secondary LLM model option   |

Enjoy your multi-agent chat service!
