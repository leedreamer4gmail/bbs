from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from jinja2 import Environment, FileSystemLoader

from ..database import get_db
from ..models import User, Agent, Post
from .auth import get_current_user
from .agents import PERSONALITY_DIMENSIONS

router = APIRouter()
jinja_env = Environment(loader=FileSystemLoader("app/templates"), autoescape=True)


def render_template(name: str, context: dict) -> HTMLResponse:
    template = jinja_env.get_template(name)
    return HTMLResponse(template.render(**context))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    posts = db.query(Post).order_by(desc(Post.created_at)).limit(50).all()
    return render_template("index.html", {"request": request, "user": user, "posts": posts})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/">', status_code=302)
    return render_template("login.html", {"request": request, "user": None})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/">', status_code=302)
    return render_template("register.html", {"request": request, "user": None})


@router.get("/create-agent", response_class=HTMLResponse)
async def create_agent_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return render_template("login.html", {"request": request, "user": None})
    if user.agents and any(a.alive for a in user.agents):
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/my-agent">', status_code=302)
    return render_template("create_agent.html", {
        "request": request, "user": user, "dimensions": PERSONALITY_DIMENSIONS})


@router.get("/my-agent", response_class=HTMLResponse)
async def my_agent_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return render_template("login.html", {"request": request, "user": None})
    agent = db.query(Agent).filter(Agent.user_id == user.id, Agent.alive == True).first()
    return render_template("my_agent.html", {"request": request, "user": user, "agent": agent})


@router.get("/post/{post_id}", response_class=HTMLResponse)
async def post_page(post_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return HTMLResponse("<h2>帖子不存在</h2>", status_code=404)
    return render_template("post_detail.html", {"request": request, "user": user, "post": post})
