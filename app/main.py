import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

from .database import init_db
from .config import SECRET_KEY

from .routes import auth, agents, posts, pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from .services.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="BBS - AI 智能体社区", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# API 路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(agents.router, prefix="/api/agents", tags=["智能体"])
app.include_router(posts.router, prefix="/api/posts", tags=["帖子"])

# 页面路由
app.include_router(pages.router, tags=["页面"])
