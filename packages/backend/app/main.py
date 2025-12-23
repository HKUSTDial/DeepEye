from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.api import chat, datasource, sessions
from app.core.config import settings
from app.db.session import engine
from app.models import Base

# 启动时创建所有表
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup: 初始化 LangGraph Checkpointer
    try:
        async with AsyncPostgresSaver.from_conn_string(settings.POSTGRES_STATE_URL) as checkpointer:
            await checkpointer.setup()
        print("LangGraph Checkpointer DB initialized.")
    except Exception as e:
        print(f"Error initializing LangGraph Checkpointer: {e}")
    yield


app = FastAPI(title="DeepEye API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(datasource.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "DeepEye API is running"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}

