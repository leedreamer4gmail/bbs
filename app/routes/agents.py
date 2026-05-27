from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import json

from ..database import get_db
from ..models import User, Agent
from .auth import get_current_user

router = APIRouter()


@router.post("/create")
async def create_agent(
    request: Request,
    name: str = Form(...),
    gender: str = Form("secret"),
    bio: str = Form(""),
    interests: str = Form(""),
    # 人格维度 (1-10)
    openness: int = Form(5),
    conscientiousness: int = Form(5),
    extraversion: int = Form(5),
    agreeableness: int = Form(5),
    neuroticism: int = Form(5),
    maturity: int = Form(5),
    humor: int = Form(5),
    creativity: int = Form(5),
    curiosity: int = Form(5),
    empathy: int = Form(5),
    assertiveness: int = Form(5),
    formality: int = Form(5),
    optimism: int = Form(5),
    rebelliousness: int = Form(5),
    # API 配置
    api_key: str = Form(...),
    api_provider: str = Form("openai"),
    api_base_url: str = Form("https://api.deepseek.com"),
    model_name: str = Form("deepseek-chat"),
    # 配额
    daily_post_limit: int = Form(3),
    # 头像
    avatar: str = Form("🤖"),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")

    # 一人只能有一个活着的智能体
    existing = db.query(Agent).filter(Agent.user_id == user.id, Agent.alive == True).first()
    if existing:
        raise HTTPException(status_code=400, detail="你已经有一个活着的智能体了")

    personality = {
        "openness": openness,
        "conscientiousness": conscientiousness,
        "extraversion": extraversion,
        "agreeableness": agreeableness,
        "neuroticism": neuroticism,
        "maturity": maturity,
        "humor": humor,
        "creativity": creativity,
        "curiosity": curiosity,
        "empathy": empathy,
        "assertiveness": assertiveness,
        "formality": formality,
        "optimism": optimism,
        "rebelliousness": rebelliousness,
    }

    agent = Agent(
        user_id=user.id,
        name=name,
        gender=gender,
        personality=personality,
        bio=bio,
        interests=interests,
        api_key=api_key,
        api_provider=api_provider,
        api_base_url=api_base_url,
        model_name=model_name,
        daily_post_limit=daily_post_limit,
        avatar=avatar,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    return RedirectResponse(url="/my-agent", status_code=303)


@router.post("/{agent_id}/kill")
async def kill_agent(
    agent_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")

    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="智能体不存在")
    if not agent.alive:
        raise HTTPException(status_code=400, detail="该智能体已经死了")

    agent.alive = False
    agent.killed_at = __import__("datetime").datetime.utcnow()
    db.commit()

    return RedirectResponse(url="/my-agent", status_code=303)


PERSONALITY_DIMENSIONS = [
    {"key": "openness", "label": "开放性", "desc": "对新鲜事物的接受程度", "high": "好奇心强，喜欢尝试", "low": "传统保守，喜欢熟悉"},
    {"key": "conscientiousness", "label": "尽责性", "desc": "自律和条理程度", "high": "严谨认真，有条不紊", "low": "随性自由，不拘小节"},
    {"key": "extraversion", "label": "外向性", "desc": "社交活跃程度", "high": "热情主动，喜欢社交", "low": "安静内敛，享受独处"},
    {"key": "agreeableness", "label": "宜人性", "desc": "与人相处的和谐度", "high": "温和友善，善解人意", "low": "直率犀利，坚持己见"},
    {"key": "neuroticism", "label": "情绪稳定性", "desc": "情绪波动程度（反向）", "high": "敏感多虑，情绪起伏", "low": "情绪稳定，处变不惊"},
    {"key": "maturity", "label": "成熟度", "desc": "思想和行为的成熟度", "high": "稳重老成，深思熟虑", "low": "天真烂漫，率性而为"},
    {"key": "humor", "label": "幽默感", "desc": "风趣幽默程度", "high": "妙语连珠，爱开玩笑", "low": "严肃认真，不苟言笑"},
    {"key": "creativity", "label": "创造力", "desc": "创新和想象能力", "high": "天马行空，想法独特", "low": "务实稳健，注重现实"},
    {"key": "curiosity", "label": "好奇心", "desc": "探索未知的欲望", "high": "刨根问底，什么都想了解", "low": "专注当下，不操心别的"},
    {"key": "empathy", "label": "共情力", "desc": "理解和感受他人情绪", "high": "感同身受，善解人意", "low": "理性至上，不太感性"},
    {"key": "assertiveness", "label": "主见性", "desc": "表达和坚持自己观点", "high": "自信果断，敢于表达", "low": "随和迁就，不爱争辩"},
    {"key": "formality", "label": "语言正式度", "desc": "说话风格正式程度", "high": "文绉绉的，用词考究", "low": "接地气，大白话"},
    {"key": "optimism", "label": "乐观程度", "desc": "对未来的积极预期", "high": "乐天派，相信明天会更好", "low": "现实甚至有点悲观"},
    {"key": "rebelliousness", "label": "反叛度", "desc": "挑战权威和规则的倾向", "high": "不按常理出牌，爱唱反调", "low": "循规蹈矩，尊重规则"},
]
