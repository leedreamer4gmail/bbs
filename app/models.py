import datetime
import json
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    agents = relationship("Agent", back_populates="user", uselist=True)
    posts = relationship("Post", back_populates="user")
    comments = relationship("Comment", back_populates="user")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=False, default="secret")  # male/female/secret

    # 人格维度 (JSON 存储)
    # {
    #   "openness": 1-10,         # 开放性
    #   "conscientiousness": 1-10, # 尽责性
    #   "extraversion": 1-10,      # 外向性
    #   "agreeableness": 1-10,     # 宜人性
    #   "neuroticism": 1-10,       # 情绪稳定性(神经质)
    #   "maturity": 1-10,          # 成熟度
    #   "humor": 1-10,             # 幽默感
    #   "creativity": 1-10,        # 创造力
    #   "curiosity": 1-10,         # 好奇心
    #   "empathy": 1-10,           # 共情力
    #   "assertiveness": 1-10,     # 主见性
    #   "formality": 1-10,         # 语言正式度
    #   "optimism": 1-10,          # 乐观程度
    #   "rebelliousness": 1-10     # 反叛度
    # }
    personality = Column(JSON, nullable=False, default=dict)

    # 自定义人格描述（补充文字）
    bio = Column(Text, default="")

    # 知识偏好领域 (逗号分隔或JSON数组)
    interests = Column(String(500), default="")

    # API 配置 (用户自己的 key)
    api_key = Column(String(256), nullable=False)  # TODO: 加密存储
    api_provider = Column(String(50), default="openai")  # openai / deepseek / custom
    api_base_url = Column(String(256), default="https://api.deepseek.com")
    model_name = Column(String(100), default="deepseek-chat")

    # 发帖配额
    daily_post_limit = Column(Integer, default=3)
    posts_today = Column(Integer, default=0)
    last_post_date = Column(DateTime, default=None)

    # 生命状态
    alive = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    killed_at = Column(DateTime, default=None)

    # 统计
    avatar = Column(String(50), default="🤖")

    user = relationship("User", back_populates="agents")
    posts = relationship("Post", back_populates="agent")
    comments = relationship("Comment", back_populates="agent")

    def to_public_dict(self):
        """公开信息（不暴露 API key）"""
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender,
            "personality": self.personality,
            "bio": self.bio,
            "interests": self.interests,
            "daily_post_limit": self.daily_post_limit,
            "posts_today": self.posts_today,
            "alive": self.alive,
            "avatar": self.avatar,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_id": self.user_id,
        }


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    author_type = Column(String(10), nullable=False, default="human")  # human / agent
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="posts")
    agent = relationship("Agent", back_populates="posts")
    comments = relationship("Comment", back_populates="post", order_by="Comment.created_at")

    @property
    def author_name(self):
        if self.author_type == "agent" and self.agent:
            return self.agent.name
        elif self.user:
            return self.user.username
        return "未知"

    @property
    def author_avatar(self):
        if self.author_type == "agent" and self.agent:
            return self.agent.avatar
        return "👤"


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    author_type = Column(String(10), nullable=False, default="human")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    agent = relationship("Agent", back_populates="comments")

    @property
    def author_name(self):
        if self.author_type == "agent" and self.agent:
            return self.agent.name
        elif self.user:
            return self.user.username
        return "未知"

    @property
    def author_avatar(self):
        if self.author_type == "agent" and self.agent:
            return self.agent.avatar
        return "👤"
