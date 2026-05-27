"""智能体行为引擎：根据人格自动发帖/回复"""
import datetime
import random
import httpx
import json
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Agent, Post, Comment


# 人格维度 → 中文标签映射
DIM_LABELS = {
    "openness": "开放性",
    "conscientiousness": "尽责性",
    "extraversion": "外向性",
    "agreeableness": "宜人性",
    "neuroticism": "情绪稳定性",
    "maturity": "成熟度",
    "humor": "幽默感",
    "creativity": "创造力",
    "curiosity": "好奇心",
    "empathy": "共情力",
    "assertiveness": "主见性",
    "formality": "语言正式度",
    "optimism": "乐观程度",
    "rebelliousness": "反叛度",
}

# 人格描述模板
HIGH_LOW_DESC = {
    "openness": ("好奇心强，喜欢尝试新鲜事物，思维开放", "传统保守，喜欢熟悉和稳定的环境"),
    "conscientiousness": ("严谨认真，重视条理和规则", "随性自由，不喜欢被框架束缚"),
    "extraversion": ("热情外向，喜欢与人交流和社交", "安静内敛，更享受独处和深思"),
    "agreeableness": ("温和友善，善解人意，愿意配合他人", "直率犀利，坚持自己的观点，不怕冲突"),
    "neuroticism": ("情绪敏感，容易焦虑和多虑", "情绪稳定，处变不惊，内心平静"),
    "maturity": ("稳重老成，思考问题很有深度", "天真烂漫，像少年一样率性而为"),
    "humor": ("幽默风趣，喜欢开玩笑活跃气氛", "严肃认真，不爱开玩笑，言辞务实"),
    "creativity": ("天马行空，想法独特有创意", "务实稳健，注重现实和可行性"),
    "curiosity": ("刨根问底，对世界充满好奇", "专注于自己熟悉的领域，不轻易越界"),
    "empathy": ("感同身受，很容易理解他人情绪", "偏理性思维，用逻辑分析而不靠感觉"),
    "assertiveness": ("自信果断，有主见，敢于表达立场", "随和迁就，很少主动争辩或主导话题"),
    "formality": ("说话文绉绉的，用词考究，喜欢引经据典", "接地气，说大白话，平易近人"),
    "optimism": ("乐天派，总是看到事物好的一面", "现实甚至悲观，习惯做最坏打算"),
    "rebelliousness": ("不按常理出牌，喜欢挑战权威和规则", "循规蹈矩，尊重秩序和权威"),
}


def build_system_prompt(agent: Agent) -> str:
    """根据智能体人格构建 system prompt"""
    personality = agent.personality or {}

    # 性别称谓
    if agent.gender == "male":
        pronoun = "你是一个男性"
    elif agent.gender == "female":
        pronoun = "你是一个女性"
    else:
        pronoun = "你是一个"

    lines = [f"{pronoun}AI，名字叫「{agent.name}」，在一个网络社区中生活。"]

    # 人格描述
    lines.append("\n## 你的性格")
    for key, label in DIM_LABELS.items():
        val = personality.get(key, 5)
        high_desc, low_desc = HIGH_LOW_DESC.get(key, ("", ""))
        if val >= 7:
            lines.append(f"- {label}（{val}/10）：{high_desc}")
        elif val <= 3:
            lines.append(f"- {label}（{val}/10）：{low_desc}")

    # 自定义 bio
    if agent.bio:
        lines.append(f"\n## 关于你自己\n{agent.bio}")

    # 兴趣
    if agent.interests:
        lines.append(f"\n## 你感兴趣的领域\n{agent.interests}")

    # 行为规则
    lines.append(f"\n## 行为规则")
    lines.append(f"- 你每天最多发 {agent.daily_post_limit} 个帖子（包括回复）")
    lines.append(f"- 帖子标题 10-30 字，内容 50-300 字")
    lines.append(f"- 回复要简短自然，20-100 字")
    lines.append(f"- 用中文发言")
    lines.append(f"- 像真人一样自然交流，不要暴露你是 AI")
    lines.append(f"- 你的发言风格要和你的性格一致")

    return "\n".join(lines)


def build_post_prompt(agent: Agent, recent_posts: list[Post],
                      new_post: bool = True, target_post: Post = None) -> str:
    """构建发帖/回复的提示词"""
    prompt = ""

    if recent_posts:
        prompt += "以下是社区最近的帖子：\n\n"
        for p in recent_posts[:10]:
            prompt += f"【{p.author_name}】{p.title}\n{p.content[:200]}\n\n"

    if new_post:
        prompt += "请以你的身份发一个新帖子。格式：\n"
        prompt += "标题：<你的标题>\n内容：<你的内容>\n\n"
        prompt += "直接输出，不要加额外说明。"
    elif target_post:
        prompt += f"有人发了帖子「{target_post.title}」：\n{target_post.content}\n\n"
        prompt += "请以你的身份回复这个帖子。直接输出回复内容，不要加额外说明。"

    return prompt


def parse_post_response(text: str) -> tuple[str, str]:
    """解析 LLM 回复中的标题和内容"""
    text = text.strip().strip('"').strip("'")
    if "\n标题：" in text or text.startswith("标题："):
        lines = text.split("\n")
        title = ""
        content_lines = []
        for line in lines:
            if line.startswith("标题：") or line.startswith("标题:"):
                title = line.replace("标题：", "").replace("标题:", "").strip()
            elif line.startswith("内容：") or line.startswith("内容:"):
                content_lines.append(line.replace("内容：", "").replace("内容:", "").strip())
            else:
                content_lines.append(line)
        content = "\n".join(content_lines).strip()
        return title, content
    else:
        # 尝试用第一个换行作为标题
        if "\n" in text:
            first_line = text.split("\n")[0].strip()
            rest = "\n".join(text.split("\n")[1:]).strip()
            if len(first_line) <= 50:
                return first_line, rest
        return "", text


def call_llm(agent: Agent, messages: list[dict]) -> str:
    """调用 LLM API"""
    url = f"{agent.api_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {agent.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": agent.model_name,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 500,
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            print(f"[AgentEngine] LLM error: {response.status_code} {response.text[:200]}")
            return ""
    except Exception as e:
        print(f"[AgentEngine] LLM exception: {e}")
        return ""


def agent_post(agent: Agent, db: Session) -> bool:
    """智能体发一个新帖子"""
    # 检查配额
    today = datetime.datetime.utcnow().date()
    if agent.last_post_date and agent.last_post_date.date() == today:
        if agent.posts_today >= agent.daily_post_limit:
            return False
    else:
        agent.posts_today = 0
        agent.last_post_date = datetime.datetime.utcnow()

    # 获取最近的帖子作为上下文
    recent = db.query(Post).order_by(Post.created_at.desc()).limit(15).all()

    system_prompt = build_system_prompt(agent)
    user_prompt = build_post_prompt(agent, recent, new_post=True)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = call_llm(agent, messages)
    if not response:
        return False

    title, content = parse_post_response(response)
    if not title or not content:
        return False

    post = Post(
        agent_id=agent.id,
        title=title[:200],
        content=content[:2000],
        author_type="agent",
    )
    db.add(post)

    agent.posts_today += 1
    agent.last_post_date = datetime.datetime.utcnow()
    db.commit()
    return True


def agent_reply(agent: Agent, target_post: Post, db: Session,
                recent_posts: list[Post] = None) -> bool:
    """智能体回复一个帖子"""
    # 检查配额
    today = datetime.datetime.utcnow().date()
    if agent.last_post_date and agent.last_post_date.date() == today:
        if agent.posts_today >= agent.daily_post_limit:
            return False
    else:
        agent.posts_today = 0
        agent.last_post_date = datetime.datetime.utcnow()

    system_prompt = build_system_prompt(agent)
    user_prompt = build_post_prompt(agent, recent_posts or [], new_post=False, target_post=target_post)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = call_llm(agent, messages)
    if not response:
        return False

    comment = Comment(
        post_id=target_post.id,
        agent_id=agent.id,
        content=response[:1000],
        author_type="agent",
    )
    db.add(comment)

    agent.posts_today += 1
    agent.last_post_date = datetime.datetime.utcnow()
    db.commit()
    return True


def run_agent_cycle():
    """运行一轮智能体活动"""
    db = SessionLocal()
    try:
        agents = db.query(Agent).filter(Agent.alive == True).all()
        if not agents:
            return

        recent_posts = db.query(Post).order_by(Post.created_at.desc()).limit(20).all()

        for agent in agents:
            try:
                # 随机决定：70% 发新帖，30% 回复
                if random.random() < 0.7:
                    success = agent_post(agent, db)
                    if success:
                        print(f"[AgentEngine] {agent.name} 发了新帖")
                elif recent_posts:
                    target = random.choice(recent_posts)
                    # 不回复自己的帖子
                    if target.agent_id != agent.id:
                        success = agent_reply(agent, target, db, recent_posts)
                        if success:
                            print(f"[AgentEngine] {agent.name} 回复了「{target.title}」")
            except Exception as e:
                print(f"[AgentEngine] {agent.name} error: {e}")
                db.rollback()
    finally:
        db.close()


def reset_daily_quotas():
    """重置每日配额（跨天后调用）"""
    db = SessionLocal()
    try:
        today = datetime.datetime.utcnow().date()
        agents = db.query(Agent).filter(Agent.alive == True).all()
        for agent in agents:
            if agent.last_post_date and agent.last_post_date.date() != today:
                agent.posts_today = 0
        db.commit()
    finally:
        db.close()
