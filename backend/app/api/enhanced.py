"""增强API — 插件式增量，不重构现有代码"""
from datetime import date, datetime
from fastapi import APIRouter, Query
from app.database import get_connection

router = APIRouter()


# ==================== 首页增强数据 ====================

@router.get("/homepage-enhanced")
def get_homepage_enhanced():
    """首页增强数据：市场状态 + 自动交易状态 + 动态因子权重 + 策略状态"""
    from app.services.cache import cache

    cached = cache.get("enhanced:homepage")
    if cached:
        return {"code": 0, "data": cached, "message": "ok (cached)"}

    # 1. 市场状态
    regime_data = _get_market_regime()

    # 2. 自动交易状态
    from app.trading.auto_trader import auto_trader
    trader_status = auto_trader.get_status()

    # 3. 动态因子权重
    from app.factors.alpha_model import alpha_model
    factor_data = alpha_model.get_report()

    # 4. 策略状态
    from app.health.scorer import health_scorer
    health = health_scorer.scores
    weights = health_scorer.get_weights()
    strategy_list = []
    for name, s in health.items():
        strategy_list.append({
            "name": name,
            "health_score": s["health_score"],
            "win_rate": s["win_rate"],
            "profit_loss_ratio": s["profit_loss_ratio"],
            "max_drawdown": s["max_drawdown"],
            "status": s["status"],
            "weight": weights.get(name, 0),
            "total_trades": s["total_trades"],
        })

    # 5. 综合风控状态
    risk_status = _get_risk_status()

    result = {
        "market_regime": regime_data,
        "auto_trader": {
            "is_running": trader_status.get("is_running", False),
            "cycles": trader_status.get("cycles", 0),
            "trades_today": trader_status.get("trades_today", 0),
            "interval": trader_status.get("interval", 5),
            "last_error": trader_status.get("last_error", ""),
        },
        "factor_weights": {
            "weights": factor_data.get("weights", {}),
            "active_factors": factor_data.get("active_factors", []),
            "performance": factor_data.get("performance", {}),
        },
        "strategies": strategy_list,
        "risk_status": risk_status,
        "timestamp": datetime.now().isoformat(),
    }

    cache.set("enhanced:homepage", result, ttl=10)
    return {"code": 0, "data": result, "message": "ok"}


def _get_market_regime():
    """获取市场状态数据"""
    try:
        from app.regime.detector import MarketRegimeDetector
        detector = MarketRegimeDetector()
        r = detector.classify_full()
        if r:
            return {
                "trend": r.trend_regime,
                "volatility": r.volatility_regime,
                "sentiment_stage": r.sentiment_stage,
                "position_advice": r.position_suggestion,
                "risk_level": "HIGH" if r.trend_regime == "bear" else ("MEDIUM" if r.volatility_regime == "high" else "LOW"),
            }
    except Exception as e:
        print(f"[增强] 市场状态获取失败: {e}")
    return {"trend": "unknown", "volatility": "unknown", "sentiment_stage": "unknown", "position_advice": 0, "risk_level": "UNKNOWN"}


def _get_risk_status():
    """获取综合风控状态"""
    try:
        from app.risk.circuit_breaker import circuit_breaker
        from app.risk.drawdown_protection import drawdown_protection
        from app.risk.loss_protection import loss_protection

        cb = circuit_breaker.get_status()
        dd = drawdown_protection.get_status()
        lp = loss_protection.get_all_status()

        return {
            "circuit_breakers": cb,
            "drawdown": dd,
            "loss_protection": lp,
            "overall": "safe" if not _has_breach(cb, dd) else "warning",
        }
    except Exception as e:
        return {"overall": "unknown", "error": str(e)}


def _has_breach(cb, dd):
    for v in (cb or {}).values():
        if isinstance(v, dict) and v.get("blocked"):
            return True
    if isinstance(dd, dict) and dd.get("blocked"):
        return True
    return False


# ==================== 选股增强：AI买入原因 + 风险提示 ====================

@router.get("/scan/ai-reason/{code}")
def get_ai_buy_reason(code: str):
    """基于多因子和策略信号生成AI买入原因"""
    # 30 分钟缓存：避免同一只股票频繁点击导致 LLM 重复消耗
    from app.services.cache import cache
    cached = cache.get(f"scan:ai_reason:{code}")
    if cached:
        return {"code": 0, "data": cached, "message": "ok (cached)"}

    from app.factors.alpha_model import alpha_model
    from app.scanner.full_scanner import batch_tencent_quotes
    from app.scanner.tech_score import calc_tech_score

    quotes = batch_tencent_quotes([code])
    stock = quotes.get(code, {})
    if not stock:
        return {"code": 1, "data": None, "message": "未获取到行情"}

    stock["code"] = code

    # Alpha综合评分
    alpha = alpha_model.compute_alpha(stock)

    # 技术评分
    tech_result = calc_tech_score(stock) if stock.get("price", 0) > 0 else {}
    tech = tech_result.get("total_score", 0) if isinstance(tech_result, dict) else 0

    # === 注入 efinance + TA-Lib + 机构行为数据 ===
    enriched = _enrich_stock_for_ai(stock)

    # 构造额外上下文给 LLM
    extra_context = _build_ai_extra_context(enriched)

    # 生成原因（优先用真实LLM，失败则规则兜底）
    from app.services.ai_service import ai_service
    ai_text = ai_service.buy_reason(
        code=code, name=stock.get("name", ""),
        price=stock.get("price", 0), change_pct=stock.get("change_pct", 0) or 0,
        turnover_pct=stock.get("turnover_pct", 0) or 0,
        pe_ttm=stock.get("pe_ttm", 0) or 0,
        alpha_score=alpha, tech_score=tech,
        extra_context=extra_context,
    )
    # 拆分为列表用于前端展示
    if ai_text:
        reasons = [s.strip() for s in ai_text.replace("；", ";").replace("。", ";").split(";") if s.strip()]
    else:
        reasons = _build_ai_reasons(enriched, alpha, tech)  # 规则兜底（用增强后的数据）
    result_data = {
        "code": code,
        "name": stock.get("name", ""),
        "alpha_score": alpha,
        "tech_score": tech,
        "reasons": reasons,
        "summary": "；".join(reasons[:3]) if reasons else "暂无明确的买入信号",
        # 新增：机构行为 + 资金流概要（供前端展示）
        "main_force_pace": enriched.get("main_force_pace", ""),
        "main_force_strength": enriched.get("main_force_strength", 0),
        "pace_desc": enriched.get("pace_desc", ""),
        "sector": enriched.get("sector", ""),
        "board_count": enriched.get("board_count", 0),
        "main_net_inflow": enriched.get("main_net_inflow", 0),
        "main_net_5d": enriched.get("main_net_5d", 0),
    }
    cache.set(f"scan:ai_reason:{code}", result_data, ttl=1800)  # 30 分钟
    return {"code": 0, "data": result_data, "message": "ok"}


def _enrich_stock_for_ai(stock: dict) -> dict:
    """为单只股票补充 efinance + TA-Lib + 机构行为数据

    优先从 market_cache 获取（毫秒级），不存在则实时拉取（秒级）。
    """
    import logging
    logger = logging.getLogger(__name__)
    code = stock.get("code", "")
    enriched = dict(stock)

    # 1. 优先从 market_cache 获取 efinance 字段（毫秒级，已有缓存）
    try:
        from app.services.market_cache import market_cache
        ef_data = market_cache.efinance_data.get(code, {})
        if ef_data:
            enriched.update(ef_data)
    except Exception as e:
        logger.debug("[AI增强] market_cache 获取失败: %s", e)

    # 2. 如果 market_cache 没有，实时调用 efinance 补充（秒级）
    if not enriched.get("sector") and not enriched.get("main_net_inflow"):
        try:
            from app.datasources.efinance_source import enrich_candidate
            enrich_candidate(enriched)
        except Exception as e:
            logger.debug("[AI增强] efinance 实时补充失败: %s", e)

    # 3. TA-Lib 技术指标（需要K线数据）
    if not enriched.get("ma20"):
        try:
            from app.datasources.talib_indicator import calculate_indicators
            klines = enriched.get("_klines") or []
            if not klines:
                # 从 market_cache 获取 K 线
                try:
                    from app.services.market_cache import market_cache
                    klines = market_cache.klines.get(code, []) or []
                except Exception:
                    pass
            if klines and len(klines) >= 10:
                indicators = calculate_indicators(klines)
                if indicators:
                    enriched.update(indicators)
        except Exception as e:
            logger.debug("[AI增强] TA-Lib 指标计算失败: %s", e)

    # 4. 机构行为分析（如果还没有）
    if not enriched.get("main_force_pace"):
        try:
            from app.datasources.institution_tracker import analyze_main_force_pace
            pace = analyze_main_force_pace(enriched)
            enriched.update(pace)
        except Exception as e:
            logger.debug("[AI增强] 机构行为分析失败: %s", e)

    return enriched


def _build_ai_extra_context(stock: dict) -> str:
    """构造给 LLM 的额外上下文（资金流/机构行为/板块/技术指标）"""
    parts = []

    # 板块
    sector = stock.get("sector", "")
    if sector:
        sector_pct = stock.get("sector_change_pct", 0)
        parts.append(f"板块：{sector}({sector_pct:+.1f}%)")

    # 连板
    board_count = stock.get("board_count", 0)
    if board_count > 0:
        parts.append(f"连板：{board_count}板")

    # 资金流
    main_net = stock.get("main_net_inflow", 0)
    main_net_5d = stock.get("main_net_5d", 0)
    today_net = stock.get("today_main_net", 0)
    if main_net or today_net:
        net_desc = f"主力净流入{main_net/1e8:.2f}亿"
        if today_net:
            net_desc += f"(今日{today_net/1e8:.2f}亿)"
        if main_net_5d:
            net_desc += f" 5日{main_net_5d/1e8:.2f}亿"
        parts.append(net_desc)

    # 机构行为
    pace = stock.get("main_force_pace", "")
    pace_desc = stock.get("pace_desc", "")
    if pace and pace != "unknown":
        strength = stock.get("main_force_strength", 0)
        parts.append(f"主力节奏：{pace_desc}(强度{strength})")

    # 技术指标
    macd_cross = stock.get("macd_cross", "")
    if macd_cross == "golden":
        parts.append("MACD金叉")
    elif macd_cross == "dead":
        parts.append("MACD死叉")

    rsi14 = stock.get("rsi14", 0)
    if rsi14 and 0 < rsi14 < 100:
        if rsi14 < 30:
            parts.append(f"RSI{rsi14:.0f}超卖")
        elif rsi14 > 70:
            parts.append(f"RSI{rsi14:.0f}超买")

    breakout = stock.get("breakout_20d", False)
    if breakout:
        parts.append("突破20日新高")

    return " | ".join(parts) if parts else ""


def _build_ai_reasons(stock: dict, alpha: float, tech: float) -> list:
    """构建AI买入原因列表"""
    reasons = []
    change_pct = stock.get("change_pct", 0) or 0
    turnover = stock.get("turnover_pct", 0) or 0
    pe = stock.get("pe_ttm", 0) or 0
    pb = stock.get("pb", 0) or 0
    amount = stock.get("amount", 0) or 0

    if alpha >= 80:
        reasons.append(f"Alpha综合评分{alpha}分，多因子共振强烈买入信号")
    elif alpha >= 60:
        reasons.append(f"Alpha评分{alpha}分，多因子偏向正面")

    if tech >= 80 and tech > 0:
        reasons.append(f"技术面评分{tech}分，量价形态健康")
    elif 50 <= tech < 80:
        reasons.append(f"技术面评分{tech}分，趋势尚可")

    if change_pct > 3:
        reasons.append(f"当日涨幅{change_pct:.1f}%，资金主动买入意愿强")
    elif change_pct < -3:
        reasons.append(f"回调{abs(change_pct):.1f}%，可能形成低吸机会")

    if 3 <= turnover <= 15:
        reasons.append(f"换手率{turnover:.1f}%处于活跃区间，流动性良好")
    elif turnover > 15:
        reasons.append(f"换手率{turnover:.1f}%偏高，注意短线博弈风险")

    if 0 < pe < 30:
        reasons.append(f"PE(TTM){pe:.1f}倍，估值处于合理偏低区间")
    elif 0 < pb < 2:
        reasons.append(f"PB{pb:.2f}倍，低于净资产附近")

    if amount > 5e8:
        reasons.append(f"成交额{(amount/1e8):.1f}亿，市场关注度较高")

    # === 新增：efinance + 机构行为原因 ===
    # 板块
    sector = stock.get("sector", "")
    sector_pct = stock.get("sector_change_pct", 0) or 0
    if sector:
        if sector_pct > 2:
            reasons.append(f"所属板块{sector}涨{sector_pct:.1f}%，板块效应明显")
        elif sector_pct > 0:
            reasons.append(f"所属板块{sector}上涨{sector_pct:.1f}%")

    # 连板
    board_count = stock.get("board_count", 0) or 0
    if board_count >= 2:
        reasons.append(f"{board_count}连板，市场人气龙头")

    # 资金流
    main_net = stock.get("main_net_inflow", 0) or 0
    main_net_5d = stock.get("main_net_5d", 0) or 0
    if main_net > 0:
        reasons.append(f"主力净流入{main_net/1e8:.2f}亿，资金做多意愿强")
    if main_net_5d > 0:
        reasons.append(f"5日主力净流入{main_net_5d/1e8:.2f}亿，持续吸筹")

    # 机构行为
    pace = stock.get("main_force_pace", "")
    pace_desc = stock.get("pace_desc", "")
    if pace == "accumulation":
        reasons.append(f"主力建仓信号：{pace_desc}")
    elif pace == "pulling":
        reasons.append(f"主力拉升信号：{pace_desc}")
    elif pace == "washing":
        reasons.append(f"主力洗盘信号：{pace_desc}")

    # 技术指标
    macd_cross = stock.get("macd_cross", "")
    if macd_cross == "golden":
        reasons.append("MACD金叉，短期趋势转强")
    rsi14 = stock.get("rsi14", 0) or 0
    if 0 < rsi14 < 30:
        reasons.append(f"RSI{rsi14:.0f}超卖，技术性反弹概率大")
    if stock.get("breakout_20d"):
        reasons.append("突破20日新高，上行空间打开")

    return reasons


@router.get("/scan/risk-tips/{code}")
def get_risk_tips(code: str):
    """获取个股风险提示"""
    # 30 分钟缓存
    from app.services.cache import cache
    cached = cache.get(f"scan:risk_tips:{code}")
    if cached:
        return {"code": 0, "data": cached, "message": "ok (cached)"}

    from app.risk.manager import risk_manager
    from app.scanner.full_scanner import batch_tencent_quotes

    quotes = batch_tencent_quotes([code])
    stock = quotes.get(code, {})
    if not stock:
        return {"code": 1, "data": None, "message": "未获取到行情"}

    stock["code"] = code

    # === 注入 efinance + 机构行为数据 ===
    enriched = _enrich_stock_for_ai(stock)

    result = risk_manager.check_stock(stock)
    change_pct = stock.get("change_pct", 0) or 0
    turnover = stock.get("turnover_pct", 0) or 0
    pe = stock.get("pe_ttm", 0) or 0

    tips = list(result.risk_factors) if hasattr(result, 'risk_factors') else []

    # 补充通用风险
    if change_pct > 9:
        tips.insert(0, "该股接近涨停，追高风险较大")
    if turnover > 20:
        tips.append(f"换手率{turnover:.1f}%异常偏高，存在资金博弈风险")
    if pe > 100:
        tips.append(f"PE(TTM){pe:.1f}倍，估值明显偏高")
    if pe < 0:
        tips.append("公司当前处于亏损状态，注意基本面风险")

    # === 新增：资金流 + 机构行为风险 ===
    main_net = enriched.get("main_net_inflow", 0) or 0
    main_net_5d = enriched.get("main_net_5d", 0) or 0
    today_net = enriched.get("today_main_net", 0) or 0
    if main_net < 0:
        tips.append(f"主力净流出{abs(main_net)/1e8:.2f}亿，资金撤退信号")
    if main_net_5d < 0:
        tips.append(f"5日主力净流出{abs(main_net_5d)/1e8:.2f}亿，持续出逃")
    if today_net < 0 and change_pct > 3:
        tips.append("今日主力净流出但股价上涨，顶背离风险")

    pace = enriched.get("main_force_pace", "")
    pace_desc = enriched.get("pace_desc", "")
    if pace == "distribution":
        tips.append(f"主力出货信号：{pace_desc}")

    # 板块下跌风险
    sector = enriched.get("sector", "")
    sector_pct = enriched.get("sector_change_pct", 0) or 0
    if sector and sector_pct < -2:
        tips.append(f"所属板块{sector}跌{abs(sector_pct):.1f}%，板块拖累")

    # 连板断板风险
    board_count = enriched.get("board_count", 0) or 0
    if board_count >= 3 and change_pct < 0:
        tips.append(f"{board_count}连板后回调，断板风险大")

    # 技术指标风险
    macd_cross = enriched.get("macd_cross", "")
    if macd_cross == "dead":
        tips.append("MACD死叉，短期趋势转弱")
    rsi14 = enriched.get("rsi14", 0) or 0
    if rsi14 > 80:
        tips.append(f"RSI{rsi14:.0f}超买，回调概率增大")

    # 构造额外上下文给 LLM
    extra_context = _build_risk_extra_context(enriched)

    # AI风险解读
    from app.services.ai_service import ai_service
    ai_risk = ai_service.risk_analysis(
        code=code, name=stock.get("name", ""),
        change_pct=change_pct, pe_ttm=pe, turnover_pct=turnover,
        risk_level=result.risk_level if hasattr(result, 'risk_level') else "MEDIUM",
        risk_factors=tips,
        extra_context=extra_context,
    )

    result_data = {
        "code": code,
        "name": stock.get("name", ""),
        "risk_level": result.risk_level if hasattr(result, 'risk_level') else "MEDIUM",
        "risk_factors": tips,
        "suggestion": (ai_risk or result.suggestion) if hasattr(result, 'suggestion') else "请综合评估风险",
        # 新增：机构行为概要
        "main_force_pace": pace,
        "main_force_strength": enriched.get("main_force_strength", 0),
        "pace_desc": pace_desc,
        "main_net_inflow": main_net,
    }
    cache.set(f"scan:risk_tips:{code}", result_data, ttl=1800)  # 30 分钟
    return {"code": 0, "data": result_data, "message": "ok"}


def _build_risk_extra_context(stock: dict) -> str:
    """构造风险分析的额外上下文"""
    parts = []
    main_net = stock.get("main_net_inflow", 0) or 0
    if main_net:
        parts.append(f"主力净流入{main_net/1e8:.2f}亿")
    pace = stock.get("main_force_pace", "")
    if pace and pace != "unknown":
        parts.append(f"主力节奏：{pace}")
    sector = stock.get("sector", "")
    if sector:
        parts.append(f"板块：{sector}")
    board_count = stock.get("board_count", 0) or 0
    if board_count > 0:
        parts.append(f"{board_count}连板")
    return " | ".join(parts) if parts else ""


# ==================== 交易增强：止损开关 + 最大仓位 + 风控状态 ====================

@router.get("/trade/risk-control-status")
def get_trade_risk_control():
    """交易页风控状态汇总"""
    from app.risk.circuit_breaker import circuit_breaker
    from app.risk.drawdown_protection import drawdown_protection
    from app.risk.loss_protection import loss_protection
    from app.trading.paper_engine import paper_engine

    cb = circuit_breaker.get_status()
    dd = drawdown_protection.get_status()
    lp = loss_protection.get_all_status()
    state = paper_engine.get_state()

    # 各策略熔断详情
    blocked_strategies = []
    for k, v in (cb or {}).items():
        if isinstance(v, dict) and v.get("blocked"):
            blocked_strategies.append({"strategy": k, "reason": v.get("reason", ""), "until": v.get("until", "")})

    return {"code": 0, "data": {
        "auto_stop_loss_enabled": state.get("auto_stop_loss_enabled", True),
        "max_position_pct": state.get("max_position_pct", 10),
        "max_single_strategy_pct": state.get("max_single_strategy_pct", 40),
        "drawdown_warning": dd.get("warning", False) if isinstance(dd, dict) else False,
        "drawdown_current_pct": dd.get("current_drawdown_pct", 0) if isinstance(dd, dict) else 0,
        "blocked_strategies": blocked_strategies,
        "loss_protection": lp,
        "circuit_breaker_count": sum(1 for v in (cb or {}).values() if isinstance(v, dict) and v.get("blocked")),
    }, "message": "ok"}


@router.post("/trade/toggle-stop-loss")
def toggle_stop_loss(enabled: bool = Query(True)):
    """切换自动止损开关"""
    from app.trading.paper_engine import paper_engine
    paper_engine.set_auto_stop_loss(enabled)
    return {"code": 0, "data": {"auto_stop_loss_enabled": enabled}, "message": f"自动止损已{'开启' if enabled else '关闭'}"}


@router.post("/trade/max-position")
def set_max_position(pct: float = Query(10, ge=1, le=50, description="单只股票最大仓位百分比")):
    """设置最大仓位"""
    from app.trading.paper_engine import paper_engine
    paper_engine.set_max_position_pct(pct)
    return {"code": 0, "data": {"max_position_pct": pct}, "message": f"单只最大仓位已设为{pct}%"}


# ==================== 回测增强 ====================

@router.get("/backtest/enhanced/{strategy_name}")
def enhanced_backtest(strategy_name: str, days: int = Query(60)):
    """增强回测：含滑点后收益 + 样本外 + 真实成交 + 最大回撤详情"""
    from app.backtest.engine import backtest_engine
    from app.trading.trade_ledger import trade_ledger

    # "all" 模式：聚合所有策略（取总和/均值）
    if strategy_name == "all":
        from app.health.scorer import health_scorer
        all_strategies = list(health_scorer.scores.keys())
        if not all_strategies:
            all_strategies = ["leader","first_board","second_board","leader_dip","main_wave","weak_to_strong","money_flow"]
        agg_return = 0.0; agg_win = 0; agg_trades = 0; agg_dd = 0.0; agg_cost = 0.0; count = 0
        for s_name in all_strategies:
            try:
                bt = backtest_engine.run_from_ledger(strategy=s_name)
                if bt.total_trades > 0:
                    agg_return += bt.total_return
                    agg_win += round(bt.win_rate * bt.total_trades / 100)
                    agg_trades += bt.total_trades
                    agg_dd += bt.max_drawdown
                    agg_cost += bt.total_cost
                    count += 1
            except Exception:
                pass
        return {"code": 0, "data": {
            "strategy": "all", "days": days,
            "with_slippage": {
                "total_return": round(agg_return / max(count, 1), 2),
                "win_rate": round(agg_win / max(agg_trades, 1) * 100, 1),
                "sharpe_ratio": 0, "max_drawdown": round(agg_dd / max(count, 1), 2),
                "total_trades": agg_trades,
            },
            "slippage_impact": {"total_cost": round(agg_cost, 2), "cost_per_trade": round(agg_cost / max(agg_trades, 1), 2)},
            "out_of_sample": {"grade": "S", "win_rate": 0, "avg_return": 0, "count": 0},
            "real_trades": {"total_return": round(agg_return, 2), "win_rate": round(agg_win / max(agg_trades, 1) * 100, 1), "total_trades": agg_trades, "max_drawdown": round(agg_dd / max(count, 1), 2)},
            "max_drawdown_detail": {"peak": 0, "trough": 0, "drawdown_pct": 0, "recovery_days": 0},
        }, "message": "ok"}

    # 单策略模式
    bt = backtest_engine.run_from_ledger(strategy=strategy_name)

    # 真实成交数据取近N天
    real_trades = trade_ledger.query(strategy=strategy_name, status="closed", days=days, limit=200)

    # 从真实成交计算各指标
    real_win = sum(1 for t in real_trades if (t.get("profit_amt", 0) or 0) > 0)
    real_total = len(real_trades)
    real_total_return = sum(t.get("profit_amt", 0) or 0 for t in real_trades)
    real_max_dd = _calc_max_drawdown(real_trades)

    # 计算滑点影响（基准总费用）
    total_slippage_cost = bt.total_cost if hasattr(bt, 'total_cost') else 0

    # 样本外：Walk-Forward
    out_sample = {}
    try:
        from app.review.walk_forward import wf_validator
        wf_eval = wf_validator.evaluate()
        out_sample = wf_eval.get("grades", {}).get("S", {}) if isinstance(wf_eval.get("grades"), dict) else {}
    except Exception:
        pass

    return {"code": 0, "data": {
        "strategy": strategy_name,
        "days": days,
        # 基准回测（已含滑点0.1%）
        "with_slippage": {
            "total_return": bt.total_return if hasattr(bt, 'total_return') else 0,
            "win_rate": bt.win_rate if hasattr(bt, 'win_rate') else 0,
            "sharpe_ratio": bt.sharpe_ratio if hasattr(bt, 'sharpe_ratio') else 0,
            "max_drawdown": bt.max_drawdown if hasattr(bt, 'max_drawdown') else 0,
            "total_trades": bt.total_trades if hasattr(bt, 'total_trades') else 0,
        },
        # 滑点影响
        "slippage_impact": {
            "total_cost": round(total_slippage_cost, 2),
            "cost_per_trade": round(total_slippage_cost / max(bt.total_trades, 1), 2) if hasattr(bt, 'total_trades') and bt.total_trades > 0 else 0,
        },
        # 样本外
        "out_of_sample": {
            "grade": "S",
            "win_rate": out_sample.get("win_rate", 0),
            "avg_return": out_sample.get("avg_return", 0),
            "count": out_sample.get("count", 0),
        },
        # 真实成交
        "real_trades": {
            "total_return": round(real_total_return, 2),
            "win_rate": round(real_win / real_total * 100, 1) if real_total > 0 else 0,
            "total_trades": real_total,
            "max_drawdown": round(real_max_dd, 2),
        },
        # 最大回撤详情
        "max_drawdown_detail": _get_drawdown_detail(strategy_name, days),
    }, "message": "ok"}


def _calc_max_drawdown(trades: list) -> float:
    """从交易列表计算最大回撤"""
    if not trades:
        return 0
    cumulative = 0
    peak = 0
    max_dd = 0
    for t in trades:
        cumulative += t.get("profit_amt", 0) or 0
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _get_drawdown_detail(strategy: str, days: int) -> dict:
    """获取最大回撤详情"""
    from app.risk.drawdown_protection import drawdown_protection
    from app.trading.trade_ledger import trade_ledger

    trades = trade_ledger.query(strategy=strategy, status="closed", days=days, limit=100)
    if not trades:
        return {"peak": 0, "trough": 0, "drawdown_pct": 0, "recovery_days": 0}

    cumulative = 0
    peak = 0
    max_dd = 0
    peak_day = ""
    trough_day = ""
    for t in sorted(trades, key=lambda x: x.get("entry_time", "")):
        cumulative += t.get("profit_amt", 0) or 0
        if cumulative > peak:
            peak = cumulative
            peak_day = t.get("entry_time", "")[:10]
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
            trough_day = t.get("entry_time", "")[:10]

    return {
        "peak": round(peak, 2),
        "trough": round(peak - max_dd, 2),
        "drawdown_pct": round(max_dd / peak * 100, 1) if peak > 0 else 0,
        "recovery_days": 0,
        "peak_date": peak_day,
        "trough_date": trough_day,
    }


# ==================== 复盘增强：AI总结 + 情绪变化 + 风险建议 ====================

@router.get("/review/ai-summary")
def get_ai_review_summary():
    """AI复盘总结：综合诊断 + 情绪变化 + 风险建议"""
    from app.services.cache import cache

    cached = cache.get("review:ai_summary")
    if cached:
        return {"code": 0, "data": cached, "message": "ok (cached)"}

    # 1. 回测诊断
    from app.review.diagnostic import diagnostic
    from app.review.heatmap import build_heatmap, get_signal_noise_verdict
    from app.trading.trade_ledger import trade_ledger

    trades = trade_ledger.query(status="closed", days=30, limit=200)
    trades_data = [
        {"code": t.get("code"), "strategy": t.get("strategy"),
         "profit_pct": t.get("profit_pct", 0) or 0,
         "profit_amt": t.get("profit_amt", 0) or 0,
         "entry_time": t.get("entry_time", ""),
         "exit_reason": t.get("exit_reason", ""),
         "stop_triggered": "止损" in (t.get("exit_reason", "") or "")}
        for t in trades
    ]
    diag = diagnostic.run(trades_data) if trades_data else {}

    # 2. 热力图
    hm = build_heatmap(trades_data)
    noise = get_signal_noise_verdict(hm)

    # 3. 情绪变化（历史情绪数据）
    sentiment_changes = _get_sentiment_changes()

    # 4. 风险建议
    risk_advice = _build_risk_advice(diag, hm)

    # 5. 汇总
    summary = _build_review_summary(diag, hm, noise, sentiment_changes)

    # 尝试用真实LLM生成更专业的复盘总结
    from app.services.ai_service import ai_service
    risk_contents = [r.get("content", "") for r in risk_advice]
    sentiment_change_desc = ""
    if len(sentiment_changes) >= 2:
        latest = sentiment_changes[-1]
        prev = sentiment_changes[-2]
        if latest.get("score", 50) > prev.get("score", 50):
            sentiment_change_desc = f"从{prev.get('stage', '')}回暖到{latest.get('stage', '')}"
        elif latest.get("score", 50) < prev.get("score", 50):
            sentiment_change_desc = f"从{prev.get('stage', '')}降温到{latest.get('stage', '')}"

    ai_summary_text = ai_service.review_summary(
        diagnostic_score=diag.get("overall_score", 50) if isinstance(diag, dict) else 50,
        verdict=diag.get("verdict", "") if isinstance(diag, dict) else "",
        win_rate=sum((s.get("overall_win_rate") or 0) for s in (hm.get("signals_summary", []) if isinstance(hm, dict) else [])) / max(len(hm.get("signals_summary", [])) if isinstance(hm, dict) else 1, 1),
        total_trades=len(trades_data),
        sentiment_stage=sentiment_changes[-1].get("stage", "") if sentiment_changes else "",
        sentiment_change=sentiment_change_desc,
        risk_items=risk_contents,
    )
    if ai_summary_text:
        summary = ai_summary_text

    result = {
        "date": date.today().isoformat(),
        "summary": summary,
        "diagnostic_score": diag.get("overall_score", 0) if isinstance(diag, dict) else 0,
        "verdict": diag.get("verdict", "") if isinstance(diag, dict) else "",
        "sentiment_changes": sentiment_changes,
        "risk_advice": risk_advice,
        "noise_verdict": noise,
        "heatmap_summary": hm.get("signals_summary", []) if isinstance(hm, dict) else [],
    }

    cache.set("review:ai_summary", result, ttl=60)
    return {"code": 0, "data": result, "message": "ok"}


def _get_sentiment_changes() -> list:
    """获取近5日情绪变化

    若今日情绪未存档，则实时计算并存档到 kv_store，确保历史可查
    注：kv_store 表只有 key/value/updated_at 三列，日期从 key(sentine_YYYY-MM-DD) 提取
    """
    import json
    from datetime import date
    try:
        from app.database import get_connection
        conn = get_connection()
        today = date.today().isoformat()

        # 1. 检查今日情绪是否已存档
        today_row = conn.execute(
            "SELECT value FROM kv_store WHERE key = ?",
            (f"sentiment_{today}",)
        ).fetchone()

        if not today_row:
            # 2. 实时计算并存档
            try:
                from app.strategies.sentiment import sentiment_model
                from app.datasources.ths_hot_source import fetch_ths_hot
                hot = fetch_ths_hot() or []
                current = sentiment_model.analyze(hot) if hot else {
                    "stage": "未知", "score": 0, "action": "观望"
                }
                conn.execute(
                    "INSERT OR REPLACE INTO kv_store (key, value, updated_at) "
                    "VALUES (?, ?, datetime('now'))",
                    (f"sentiment_{today}", json.dumps(current, ensure_ascii=False))
                )
                conn.commit()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("存档今日情绪失败: %s", e)

        # 3. 查询近5日（日期从 key 提取：sentiment_YYYY-MM-DD）
        rows = conn.execute(
            "SELECT key, value FROM kv_store WHERE key LIKE 'sentiment_%' "
            "ORDER BY key DESC LIMIT 5"
        ).fetchall()
        if not rows:
            return []

        result = []
        # 反转让最早的在前
        for row in reversed(rows):
            try:
                # key 格式 sentiment_2026-06-26
                d = row["key"].replace("sentiment_", "")
                v = json.loads(row["value"]) if isinstance(row["value"], str) else row["value"]
                result.append({"date": d, "stage": v.get("stage", ""),
                               "score": v.get("score", 0), "action": v.get("action", "")})
            except Exception:
                pass
        return result
    except Exception:
        return []


def _build_risk_advice(diag: dict, hm: dict) -> list:
    """构建风险建议列表"""
    advice = []
    score = diag.get("overall_score", 50) if isinstance(diag, dict) else 50

    if score < 40:
        advice.append({"level": "high", "content": "当前诊断分数偏低，建议暂停自动交易，优先修复策略参数"})
    elif score < 60:
        advice.append({"level": "medium", "content": "诊断分数一般，建议降低仓位至50%以下，等待信号改善"})

    # 检查止损触发率
    signals = hm.get("signals_summary", []) if isinstance(hm, dict) else []
    for s in signals:
        wr = s.get("overall_win_rate") or 50
        if wr is None: wr = 50
        if wr < 40:
            advice.append({"level": "high", "content": f"{s.get('signal', '')}策略跑赢率仅{wr}%，建议降低权重或暂停该策略"})
        elif wr < 50:
            advice.append({"level": "medium", "content": f"{s.get('signal', '')}策略跑赢率{wr}%偏低，保持观察"})

    if not advice:
        advice.append({"level": "low", "content": "当前系统和策略运行正常，按现有参数继续执行"})

    return advice


def _build_review_summary(diag: dict, hm: dict, noise: dict, sentiment_changes: list) -> str:
    """生成AI复盘总结文字"""
    parts = []

    score = diag.get("overall_score", 0) if isinstance(diag, dict) else 0
    verdict = diag.get("verdict", "") if isinstance(diag, dict) else ""

    if verdict:
        parts.append(f"整体诊断：{verdict}（{score}分）")

    # 信号质量
    if isinstance(noise, dict):
        good = noise.get("good_signals", 0)
        noisy = noise.get("noise_signals", 0)
        if good + noisy > 0:
            parts.append(f"有效信号{good}个，噪音信号{noisy}个")

    # 情绪趋势
    if len(sentiment_changes) >= 2:
        latest = sentiment_changes[-1] if sentiment_changes else {}
        prev = sentiment_changes[-2] if len(sentiment_changes) >= 2 else {}
        if latest and prev:
            if latest.get("score", 50) > prev.get("score", 50):
                parts.append(f"情绪回暖：从{prev.get('stage', '')}转向{latest.get('stage', '')}")
            elif latest.get("score", 50) < prev.get("score", 50):
                parts.append(f"情绪降温：从{prev.get('stage', '')}转向{latest.get('stage', '')}")
            else:
                parts.append(f"情绪平稳：维持{latest.get('stage', '')}阶段")

    return "。".join(parts) + "。" if parts else "暂无足够数据生成总结。"


# ==================== 全系统状态API（供前端仪表盘） ====================

@router.get("/system-status")
def get_system_status():
    """获取全系统状态：行情引擎+策略生命周期+组合优化+风险预算+因子进化+AI决策"""
    from app.services.cache import cache

    cached = cache.get("system_status")
    if cached:
        return {"code": 0, "data": cached, "message": "ok (cached)"}

    result = {}

    # 1. 高级行情引擎
    try:
        from app.regime.advanced_detector import regime_engine
        if regime_engine._current_state:
            s = regime_engine._current_state
            result["market_regime"] = {
                "type": s.regime,
                "name": s.regime_name,
                "confidence": s.confidence,
                "risk_level": s.risk_level,
                "max_position": s.max_position_pct,
                "active_strategies": s.active_strategies,
                "suppressed_strategies": s.suppressed_strategies,
                "strategy_weights": s.strategy_weights,
                "updated": s.timestamp,
            }
    except Exception:
        result["market_regime"] = {"name": "未就绪"}

    # 2. 策略生命周期
    try:
        from app.strategy.lifecycle import lifecycle_manager
        result["strategy_lifecycle"] = lifecycle_manager.get_all_states()
    except Exception:
        result["strategy_lifecycle"] = []

    # 3. 组合优化
    try:
        from app.portfolio.optimizer import portfolio_optimizer
        result["portfolio"] = portfolio_optimizer.analyze()
    except Exception:
        result["portfolio"] = {}

    # 4. 风险预算
    try:
        from app.risk.risk_budget import risk_budget_engine
        result["risk_budget"] = risk_budget_engine.get_current()
    except Exception:
        result["risk_budget"] = {}

    # 5. 因子进化
    try:
        from app.factors.evolution import factor_evolution
        result["factor_evolution"] = factor_evolution.get_report()
    except Exception:
        result["factor_evolution"] = {}

    # 6. AI投资委员会决策
    try:
        from app.services.ai_committee import ai_committee
        result["ai_committee"] = ai_committee.get_latest_decision()
    except Exception:
        result["ai_committee"] = {}

    result["timestamp"] = datetime.now().isoformat()

    cache.set("system_status", result, ttl=60)
    return {"code": 0, "data": result, "message": "ok"}


# ==================== 收盘后报告API ====================

@router.get("/post-market/report")
def get_post_market_report():
    """获取最新收盘后全流程报告（ai_report字段提到顶层）"""
    from app.services.post_market_orchestrator import orchestrator
    report = orchestrator.get_latest_report()
    if report:
        ai = report.get("ai_report", {})
        # 将ai_report的关键字段提升到顶层，方便前端直接读取
        for key in ("market_review", "hotspot_analysis", "leader_analysis",
                    "trade_review", "strategy_advice", "watchlist", "trading_plan"):
            if key in ai:
                report[key] = ai[key]
        return {"code": 0, "data": report, "message": "ok"}
    return {"code": 0, "data": None, "message": "今日报告尚未生成"}


@router.get("/post-market/ai-report")
def get_daily_ai_report():
    """获取最新AI分析报告（简化版，给前端）"""
    from app.services.post_market_orchestrator import orchestrator
    report = orchestrator.get_daily_ai_report()
    if report:
        return {"code": 0, "data": report, "message": "ok"}
    # 尝试从缓存获取
    from app.services.cache import cache
    cached = cache.get("daily_ai_report")
    if cached:
        return {"code": 0, "data": cached, "message": "ok (cached)"}
    return {"code": 0, "data": None, "message": "今日AI报告尚未生成"}


@router.post("/post-market/trigger")
def trigger_post_market():
    """手动触发收盘后全流程"""
    from app.services.post_market_orchestrator import orchestrator
    summary = orchestrator.run_all()
    return {"code": 0, "data": {
        "total_time": summary.get("total_time_seconds", 0),
        "steps": summary.get("steps", {}),
        "errors": summary.get("errors", []),
    }, "message": "ok"}


# ===== AI晨间简报 =====

@router.get("/morning-briefing")
def get_morning_briefing():
    from app.services.ai_morning import morning_briefing
    result = morning_briefing.get_latest()
    return {"code": 0, "data": result, "message": "ok"}


# ===== 晚间6段AI分析 =====

@router.get("/ai/error-attribution")
def get_ai_error_attribution():
    from app.services.ai_post_market import ai_analyzer
    result = ai_analyzer.get_section("ai_error_attribution")
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/ai/risk-analysis")
def get_ai_risk_analysis():
    from app.services.ai_post_market import ai_analyzer
    result = ai_analyzer.get_section("ai_risk_analysis")
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/ai/factor-analysis")
def get_ai_factor_analysis():
    from app.services.ai_post_market import ai_analyzer
    result = ai_analyzer.get_section("ai_factor_analysis")
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/ai/position-advice")
def get_ai_position_advice():
    from app.services.ai_post_market import ai_analyzer
    result = ai_analyzer.get_section("ai_position_advice")
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/ai/tomorrow-plan")
def get_ai_tomorrow_plan():
    from app.services.ai_post_market import ai_analyzer
    result = ai_analyzer.get_section("ai_tomorrow_plan")
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/ai/watchlist")
def get_ai_watchlist():
    from app.services.ai_post_market import ai_analyzer
    result = ai_analyzer.get_section("ai_watchlist")
    return {"code": 0, "data": result, "message": "ok"}


# ===== 周末深度优化 =====

@router.post("/weekend/run")
def trigger_weekend_optimization():
    from app.scheduler.jobs import auto_weekend_optimization
    auto_weekend_optimization()
    return {"code": 0, "data": {"triggered": True}, "message": "ok"}


@router.get("/weekend/report")
def get_weekend_report(week_start: str = None):
    from datetime import date, timedelta
    if not week_start:
        today = date.today()
        weekday = today.weekday()
        week_start = (today - timedelta(days=weekday)).isoformat()
    try:
        from app.database import get_connection
        import json
        conn = get_connection()
        row = conn.execute(
            "SELECT value FROM kv_store WHERE key = ?",
            (f"weekend_report_{week_start}",)
        ).fetchone()
        if row:
            return {"code": 0, "data": json.loads(row["value"]) if isinstance(row["value"], str) else row["value"], "message": "ok"}
    except Exception:
        pass
    return {"code": 0, "data": None, "message": "本周报告尚未生成"}


# ===== 因子健康度面板 =====

@router.get("/factors/health-dashboard")
def get_factor_health_dashboard():
    from app.factors.factor_regime import regime_factor_engine
    regime_factor_engine.detect_regime()
    regime_factor_engine.compute_daily_ic()
    dashboard = regime_factor_engine.get_health_dashboard()
    return {"code": 0, "data": dashboard, "message": "ok"}


@router.post("/factors/auto-adjust")
def trigger_factor_auto_adjust():
    from app.factors.factor_regime import regime_factor_engine
    result = regime_factor_engine.auto_adjust_weights()
    return {"code": 0, "data": result, "message": "ok"}


@router.post("/factors/ai-experiment")
def trigger_factor_ai_experiment():
    from app.factors.factor_regime import regime_factor_engine
    result = regime_factor_engine.ai_experiment()
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/factors/pool")
def get_factor_pool():
    from app.factors.factor_regime import FACTOR_POOL, ALL_FACTORS
    return {"code": 0, "data": {"pool": FACTOR_POOL, "all_factors": {k: {"weight": v["weight"], "desc": v["desc"], "active": v["active"], "category": v["category"]} for k, v in ALL_FACTORS.items()}}, "message": "ok"}


@router.get("/weekend/section/{section_name}")
def get_weekend_section(section_name: str):
    try:
        from app.database import get_connection
        import json
        conn = get_connection()
        row = conn.execute(
            "SELECT value FROM kv_store WHERE key = ?",
            (f"weekend_{section_name}",)
        ).fetchone()
        if row:
            return {"code": 0, "data": json.loads(row["value"]) if isinstance(row["value"], str) else row["value"], "message": "ok"}
    except Exception:
        pass
    return {"code": 0, "data": None, "message": "该分析尚未生成"}
