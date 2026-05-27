"""定时任务调度：触发智能体发帖 + 配额重置"""
from apscheduler.schedulers.background import BackgroundScheduler
from .agent_engine import run_agent_cycle, reset_daily_quotas

scheduler = BackgroundScheduler()


def start_scheduler():
    """启动定时任务"""
    # 每 30 分钟运行一轮智能体活动
    scheduler.add_job(run_agent_cycle, "interval", minutes=30, id="agent_cycle")
    # 每小时检查跨天配额重置
    scheduler.add_job(reset_daily_quotas, "interval", minutes=60, id="quota_reset")
    scheduler.start()
    print("[Scheduler] 定时任务已启动 (智能体每30min活跃，配额每小时检查)")


def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown(wait=False)
