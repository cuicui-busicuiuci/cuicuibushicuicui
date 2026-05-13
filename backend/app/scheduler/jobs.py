from datetime import datetime
from app.services.sync_service import run_sync_task


def sync_realtime_quotes():
    print(f"[{datetime.now()}] 同步实时行情...")
    run_sync_task("realtime_quotes")


def sync_daily_kline():
    print(f"[{datetime.now()}] 同步日K线...")
    run_sync_task("daily_kline")


def sync_ths_hot():
    print(f"[{datetime.now()}] 同步同花顺热点...")
    run_sync_task("ths_hot")


def sync_north_flow():
    print(f"[{datetime.now()}] 同步北向资金...")
    run_sync_task("north_flow")


def sync_reports():
    print(f"[{datetime.now()}] 同步研报...")
    run_sync_task("reports")


def sync_stock_list():
    print(f"[{datetime.now()}] 同步股票列表...")
    run_sync_task("stock_list")


def morning_monitor():
    """早盘监控 - 9:30开始"""
    print(f"[{datetime.now()}] 早盘监控启动...")
    from app.scheduler.monitor import market_monitor
    market_monitor.start_monitoring()


def afternoon_monitor():
    """午盘监控 - 13:00开始"""
    print(f"[{datetime.now()}] 午盘监控启动...")
    from app.scheduler.monitor import market_monitor
    market_monitor.start_monitoring()


def generate_morning_report():
    """生成午间报告 - 12:00"""
    print(f"[{datetime.now()}] 生成午间报告...")
    from app.scheduler.monitor import market_monitor
    report = market_monitor.generate_report()
    print(f"[{datetime.now()}] 午间报告已生成")
    return report


def generate_afternoon_report():
    """生成收盘报告 - 17:00"""
    print(f"[{datetime.now()}] 生成收盘报告...")
    from app.scheduler.monitor import market_monitor
    report = market_monitor.generate_report()
    print(f"[{datetime.now()}] 收盘报告已生成")
    return report


def stop_monitoring():
    """停止监控 - 15:00"""
    print(f"[{datetime.now()}] 停止监控...")
    from app.scheduler.monitor import market_monitor
    market_monitor.stop_monitoring()


def auto_full_scan():
    """盘中全A自动扫描 - 每30分钟"""
    print(f"[{datetime.now()}] 全A自动扫描...")
    try:
        from app.scanner.full_scanner import full_market_scan
        result = full_market_scan(max_stocks=0, min_score=40, with_quotes=True)
        print(f"[{datetime.now()}] 自动扫描完成: {result.get('results_count', 0)} 只入选, {result.get('scan_time_seconds', 0)}s")
    except Exception as e:
        print(f"[{datetime.now()}] 自动扫描失败: {e}")


def save_daily_signals():
    """保存每日信号快照"""
    print(f"[{datetime.now()}] 保存每日信号...")
    try:
        from app.datasources.ths_hot_source import fetch_ths_hot
        from app.strategies.manager import strategy_manager
        from app.recommendation.daily import daily_recommender
        from app.db.persistence import save_daily_recommendations, save_strategy_signals

        hot = fetch_ths_hot()
        if hot:
            strategies = {}
            for s in strategy_manager.strategies:
                signals = strategy_manager.run_strategy(s.name, hot)
                strategies[s.name] = [
                    {"code": sig.code, "name": sig.name, "price": sig.price,
                     "stop_loss": sig.stop_loss, "target_price": sig.target_price,
                     "reason": sig.reason, "risk": sig.risk, "confidence": sig.confidence}
                    for sig in signals
                ]
            save_strategy_signals(strategies)
            try:
                rec = daily_recommender.generate()
                save_daily_recommendations(rec)
            except Exception:
                pass
            print(f"[{datetime.now()}] 信号已保存: {sum(len(v) for v in strategies.values())} 条")
    except Exception as e:
        print(f"[{datetime.now()}] 保存信号失败: {e}")


def run_daily_trading():
    """每日自动交易 - 执行策略信号买卖"""
    print(f"[{datetime.now()}] ===== 开始每日自动交易 =====")
    try:
        from app.trading.paper_engine import paper_engine
        from app.datasources.ths_hot_source import fetch_ths_hot
        from app.strategies.manager import strategy_manager
        from app.api.strategy import _enrich_prices
        from app.scanner.full_scanner import batch_tencent_quotes

        hot = fetch_ths_hot()
        if not hot:
            print(f"[{datetime.now()}] 无热点数据，跳过交易")
            return

        hot = _enrich_prices(hot)
        signals = strategy_manager.run_all(hot)

        signal_dicts = []
        codes = set()
        for s in signals:
            signal_dicts.append({
                "code": s.code, "name": s.name, "strategy": s.strategy,
                "signal_type": s.signal_type, "price": s.price,
                "stop_loss": s.stop_loss, "target_price": s.target_price,
                "reason": s.reason, "confidence": s.confidence,
            })
            codes.add(s.code)

        quotes = batch_tencent_quotes(list(codes))
        orders = paper_engine.process_signals(signal_dicts, quotes)
        paper_engine.update_positions(quotes)

        print(f"[{datetime.now()}] 信号{len(signal_dicts)}个 → 成交{len(orders)}笔")
        print(f"[{datetime.now()}] 持仓{len(paper_engine.positions)}只, 现金{paper_engine.cash:.0f}元, 总资产{paper_engine.total_value:.0f}元")
    except Exception as e:
        print(f"[{datetime.now()}] 自动交易失败: {e}")


def generate_daily_trade_report():
    """生成每日交易盈亏报告 - 收盘后"""
    print(f"[{datetime.now()}] ===== 生成每日交易报告 =====")
    try:
        from app.trading.paper_engine import paper_engine
        from app.scanner.full_scanner import batch_tencent_quotes

        codes = list(paper_engine.positions.keys())
        if codes:
            quotes = batch_tencent_quotes(codes)
            paper_engine.update_positions(quotes)

        report = paper_engine.generate_daily_report()
        acc = report["account"]
        trades = report["today_trades"]

        print(f"[{datetime.now()}] ========== 每日交易报告 ==========")
        print(f"[{datetime.now()}] 日期: {report['date']}")
        print(f"[{datetime.now()}] 初始资金: {acc['initial_capital']:,.0f}元")
        print(f"[{datetime.now()}] 总资产: {acc['total_value']:,.0f}元")
        print(f"[{datetime.now()}] 总盈亏: {acc['total_profit']:+,.0f}元 ({acc['total_profit_pct']:+.2f}%)")
        print(f"[{datetime.now()}] 今日盈亏: {acc['today_pnl']:+,.0f}元")
        print(f"[{datetime.now()}] 持仓: {report['positions']['count']}只")
        print(f"[{datetime.now()}] 今日成交: {trades['total']}笔 (买{trades['buy_count']}/卖{trades['sell_count']})")

        if trades["sell_orders"]:
            print(f"[{datetime.now()}] --- 卖出明细 ---")
            for s in trades["sell_orders"]:
                print(f"[{datetime.now()}]   {s['code']} {s['name']} | {s['price']} | {s['reason']}")

        print(f"[{datetime.now()}] =================================")
    except Exception as e:
        print(f"[{datetime.now()}] 报告生成失败: {e}")
