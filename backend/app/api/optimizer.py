"""策略优化API"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/run")
def run_optimization():
    """手动触发单次优化"""
    from app.optimizer.strategy_optimizer import strategy_optimizer
    report = strategy_optimizer.get_optimization_report()
    return {"code": 0, "data": report, "message": "ok"}


@router.get("/report")
def get_optimization_report():
    """获取优化报告"""
    from app.optimizer.strategy_optimizer import strategy_optimizer
    report = strategy_optimizer.get_optimization_report()
    return {"code": 0, "data": report, "message": "ok"}


@router.post("/auto/start")
def auto_optimizer_start():
    """启动自动优化引擎"""
    from app.optimizer.auto_optimizer import auto_optimizer
    if auto_optimizer.is_running:
        return {"code": 0, "data": auto_optimizer.get_status(), "message": "已在运行中"}
    auto_optimizer.start()
    return {"code": 0, "data": auto_optimizer.get_status(), "message": "自动优化已启动"}


@router.post("/auto/stop")
def auto_optimizer_stop():
    """停止自动优化引擎"""
    from app.optimizer.auto_optimizer import auto_optimizer
    if not auto_optimizer.is_running:
        return {"code": 0, "data": auto_optimizer.get_status(), "message": "未在运行"}
    auto_optimizer.stop()
    return {"code": 0, "data": auto_optimizer.get_status(), "message": "自动优化已停止"}


@router.get("/auto/status")
def auto_optimizer_status():
    """获取自动优化引擎状态"""
    from app.optimizer.auto_optimizer import auto_optimizer
    return {"code": 0, "data": auto_optimizer.get_status(), "message": "ok"}


@router.get("/best")
def get_best_params():
    """获取各策略最优参数"""
    from app.optimizer.auto_optimizer import auto_optimizer
    return {"code": 0, "data": auto_optimizer.best_params, "message": "ok"}
