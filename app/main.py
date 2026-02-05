"""
FastAPI main application module.
Assembles the application with routes and startup/shutdown events.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import thread_routes
from app.api import token_routes
from app.api.forFutureRef import model_routes
from app.db.database import init_db
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("[ ... ] Starting up chat service...")
    init_db()
    print("[ ... ] Database initialized")
    yield
    # Shutdown
    print("[ ... ] Shutting down chat service...")


# Create FastAPI application
app = FastAPI(
    title="Multi-Agent Chat Service",
    description="A FastAPI service for managing multi-agent chat threads with persistent context and automatic summarization.",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["info"], summary="API Information")
async def root():
    return {
        "message": "Welcome to the API",
        "endpoints": {
            "documentation": "/docs",
            "web_ui": "/ui"
        },
        "description": {
            "documentation": "Interactive Swagger API documentation",
            "web_ui": "Web application interface"
        }
    }

# Include API routes
app.include_router(thread_routes.router)
app.include_router(token_routes.router)

# Serve simple single-page web UI
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/ui", tags=["ui"], summary="Serve web UI")
async def serve_ui():
    return FileResponse("app/static/index.html")


@app.get(
    "/health",
    tags=["health"],
    summary="Health check endpoint"
)
async def health_check():
    """
    Dedicated health check endpoint.
    
    **Returns:**
    - 200: Service is healthy
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
