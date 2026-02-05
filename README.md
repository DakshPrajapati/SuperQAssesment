# chat-service

A FastAPI-based chat service that provides thread-based conversations, LLM integration via OpenRouter, automatic summarization utilities, and an optional multi-agent orchestration layer.

This README is updated to reflect the current project layout and how to run the service locally.

**Highlights**

- Thread-based persistent chats with per-thread system prompts and summaries
- Pluggable LLM access through OpenRouter
- Summarization and token-counting helpers
- Simple multi-agent tooling under `app/agents/` (forFutureRef)

**Project layout**

```
chat-service/
├── app/
│   ├── agents/               # multi-agent helpers and workflows
│   │   ├── agent_definitions.py
│   │   ├── agent_service.py
│   │   ├── agent_workflow.py
│   │   └── readme.md
│   ├── api/                  # FastAPI route modules
│   │   ├── model_routes.py
│   │   ├── thread_routes.py
│   │   └── token_routes.py
│   ├── core/                 # configuration and core utilities
│   │   ├── config.py
│   │   ├── models.py
│   │   └── token_counter.py
│   ├── crud/                 # database CRUD operations
│   │   └── thread_crud.py
│   ├── db/                   # database setup and models
│   │   ├── database.py
│   │   └── models.py
│   ├── schemas/              # pydantic schemas
│   │   ├── message_schemas.py
│   │   ├── thread_schemas.py
│   │   └── agent_schemas.py
│   ├── services/             # business logic and LLM wrappers
│   │   ├── llm_service.py
│   │   ├── summarization_service.py
│   │   └── thread_service.py
│   ├── static/               # front-end static files
│   │   ├── index.html
│   │   ├── app.js
│   │   └── style.css
│   ├── utils/                # small helper utilities
│   │   └── summary_utils.py
│   └── main.py               # FastAPI app entrypoint
├── api_spec_doc/             # generated API docs (html)
├── db/
│   └── init/
│       └── init-db.sql
├── guides/                   # documentation and guides
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── QUICKSTART.md
├── SETUP.md
└── README.md
```

Quick references:

- Application entry: [app/main.py](app/main.py)
- API routes: [app/api/thread_routes.py](app/api/thread_routes.py), [app/api/model_routes.py](app/api/model_routes.py), [app/api/token_routes.py](app/api/token_routes.py)
- Agents: [app/agents](app/agents)
- DB init SQL: [db/init/init-db.sql](db/init/init-db.sql)

Prerequisites

- Docker and Docker Compose (for Docker quickstart)
- Alternatively: Python 3.9+, PostgreSQL 12+ (pgvector recommended)
- An OpenRouter API key

Quickstart (Docker)

1. Set up environment variables

Create a `.env` file in the project root (or copy the example) and add your `OPENROUTER_API_KEY`:

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
OPENROUTER_API_KEY=your_actual_api_key_here
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/chatdb
SUMMARIZATION_MODEL=openai/gpt-3.5-turbo
DEFAULT_LLM_1=google/gemini-pro
DEFAULT_LLM_2=mistralai/mistral-7b-instruct
```

2. Build and run with Docker Compose

```bash
docker-compose up --build
```

This will build the app image, start PostgreSQL (with the `pgvector` image), initialize the database, and run the FastAPI app on `http://localhost:8000`.

3. Access the application

- Web app: http://localhost:8000/ui
- FastAPI Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- API Base URL: http://localhost:8000

Common Docker commands

```bash
# Run in background
docker-compose up -d

# View logs
docker-compose logs -f app
docker-compose logs -f postgres

# Stop services
docker-compose down

# Stop and remove data
docker-compose down -v

# Rebuild without cache
docker-compose up --build --no-cache

# PostgreSQL shell
docker-compose exec postgres psql -U postgres -d chatdb
```

Notes on routes and usage

- Threads: the thread-related endpoints are implemented in [app/api/thread_routes.py](app/api/thread_routes.py).
- Models and token endpoints are in [app/api/model_routes.py](app/api/model_routes.py) and [app/api/token_routes.py](app/api/token_routes.py).
- Business logic lives in `app/services/` and database interactions in `app/crud/`.

---

### Thread Table

- `title`: Thread display name
- `system_prompt`: Static prompt guiding LLM behavior
- `created_at`: Thread creation timestamp

### Message Table

Stores individual messages with role and model information

- `id`: Primary key
- `thread_id`: Foreign key to Thread
- `sender`: Message sender identifier
- `role`: 'user' or 'agent'
- `content`: Message text
- `model_used`: LLM model name (for agent messages)
- `timestamp`: Message creation time

### Summary Table

Stores conversation summaries with vector embeddings

- `id`: Primary key
- `thread_id`: Foreign key to Thread
- `content`: Summary text
- `embedding`: Vector embedding for semantic search
- `created_at`: Summary generation time
- `message_count`: Number of messages summarized

## Configuration

Key settings in `app/core/config.py`:

```python
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/chatdb"
OPENROUTER_API_KEY = "your_api_key"
SUMMARIZATION_MODEL = "openai/gpt-3.5-turbo"
```

In `app/services/thread_service.py`:

```python
SUMMARIZATION_THRESHOLD = 10  # Summarize after every 10 messages
```

## Error Handling

The API returns appropriate HTTP status codes:

- **200**: Success
- **201**: Resource created
- **400**: Bad request (invalid input)
- **404**: Resource not found
- **500**: Server error

Error responses include a detail message:

```json
{
  "detail": "Thread 999 not found"
}
```

## Development

### Running with Hot Reload

```bash
uvicorn app.main:app --reload
```

## Troubleshooting

### "Module not found" errors

```bash
# Ensure you're in the virtual environment and installed dependencies
pip install -r requirements.txt
```

### Database connection errors

```bash
# Verify PostgreSQL is running
psql -U postgres -c "SELECT 1"

# Check your DATABASE_URL in .env
# Format: postgresql://username:password@host:port/database
```

### API Key errors

```bash
# Verify your OpenRouter API key is valid and has credits
# Check the API docs at https://openrouter.ai/docs
```

### pgvector not found

```bash
# Ensure pgvector extension is installed in PostgreSQL
psql -U postgres -d chatdb -c "CREATE EXTENSION IF NOT EXISTS vector"
```
