from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import chat, datasource
from app.db.session import engine
from app.models.datasource import Base as DataSourceBase
from app.models.chat_session import Base as ChatSessionBase
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import settings
from app.core.celery_app import celery_app  # Import Celery app to ensure configuration is loaded

# Create Database Tables on startup
DataSourceBase.metadata.create_all(bind=engine)
ChatSessionBase.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Setup LangGraph Checkpointer DB
    try:
        async with AsyncPostgresSaver.from_conn_string(settings.POSTGRES_STATE_URL) as checkpointer:
            await checkpointer.setup()
        print("LangGraph Checkpointer DB initialized successfully.")
    except Exception as e:
        print(f"Error initializing LangGraph Checkpointer DB: {e}")
    
    yield
    # Shutdown logic if needed

app = FastAPI(title="DeepEye API", version="0.1.0", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for MVP, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(datasource.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "DeepEye API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

