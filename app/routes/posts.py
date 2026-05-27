from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database import get_db
from ..models import User, Agent, Post, Comment
from .auth import get_current_user

router = APIRouter()


@router.post("/create")
async def create_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")

    post = Post(
        user_id=user.id,
        title=title,
        content=content,
        author_type="human",
    )
    db.add(post)
    db.commit()

    return RedirectResponse(url=f"/post/{post.id}", status_code=303)


@router.post("/{post_id}/comment")
async def create_comment(
    post_id: int,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    comment = Comment(
        post_id=post_id,
        user_id=user.id,
        content=content,
        author_type="human",
    )
    db.add(comment)
    db.commit()

    return RedirectResponse(url=f"/post/{post_id}", status_code=303)


@router.get("/list")
async def list_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(desc(Post.created_at)).limit(100).all()
    return {
        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "author_name": p.author_name,
                "author_avatar": p.author_avatar,
                "author_type": p.author_type,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "comment_count": len(p.comments),
            }
            for p in posts
        ]
    }


@router.get("/{post_id}")
async def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_name": post.author_name,
        "author_avatar": post.author_avatar,
        "author_type": post.author_type,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "comments": [
            {
                "id": c.id,
                "content": c.content,
                "author_name": c.author_name,
                "author_avatar": c.author_avatar,
                "author_type": c.author_type,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in post.comments
        ],
    }
