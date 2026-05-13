from datetime import datetime
from fastapi import APIRouter
from app.database import get_connection

router = APIRouter()


@router.get("/health")
def health_check():
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "code": 0,
        "data": {
            "status": "ok",
            "db": db_status,
            "timestamp": datetime.now().isoformat(),
        },
        "message": "ok",
    }


@router.get("/sync-log")
def get_sync_log(limit: int = 20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sync_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return {
        "code": 0,
        "data": [dict(row) for row in rows],
        "message": "ok",
    }


@router.post("/sync/{task_name}")
def trigger_sync(task_name: str):
    from app.services.sync_service import run_sync_task

    result = run_sync_task(task_name)
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/scheduler")
def get_scheduler_info():
    """获取调度器状态"""
    import app.main as main_module
    scheduler = getattr(main_module, "_scheduler", None)
    if not scheduler:
        return {"code": 0, "data": {"running": False, "jobs": []}, "message": "调度器未启动"}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {
        "code": 0,
        "data": {
            "running": scheduler.running,
            "jobs": jobs,
        },
        "message": "ok",
    }


@router.post("/scheduler/trigger/{job_id}")
def trigger_job(job_id: str):
    """手动触发调度任务"""
    import app.main as main_module
    scheduler = getattr(main_module, "_scheduler", None)
    if not scheduler:
        return {"code": 1, "data": None, "message": "调度器未启动"}

    job = scheduler.get_job(job_id)
    if not job:
        return {"code": 1, "data": None, "message": f"任务 {job_id} 不存在"}

    try:
        job.func()
        return {"code": 0, "data": {"job_id": job_id, "triggered": True}, "message": "ok"}
    except Exception as e:
        return {"code": 1, "data": None, "message": f"执行失败: {e}"}
