"""
自动交易引擎 — 后台线程持续轮询，秒级响应
替代原有的10分钟定时器，可随时启停
"""
import time
import threading
from datetime import datetime
from typing import Callable, Optional


class AutoTrader:
    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 状态
        self.last_run: Optional[datetime] = None
        self.last_error: str = ""
        self.cycles = 0
        self.trades_today = 0
        self.signals_last = 0
        self.orders_last = 0

        # 交易事件回调 (用于WebSocket/SSE广播)
        self._on_trade: Optional[Callable] = None
        self._on_cycle: Optional[Callable] = None

    def on_trade(self, cb: Callable):
        """注册交易事件回调 fn(orders: list)"""
        self._on_trade = cb

    def on_cycle(self, cb: Callable):
        """注册轮询完成回调 fn(status: dict)"""
        self._on_cycle = cb

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="auto-trader")
        self._thread.start()
        print(f"[AutoTrader] 自动交易已启动 (间隔{self.interval}s)")

    def stop(self):
        self._running = False
        self._stop_event.set()
        print("[AutoTrader] 自动交易已停止")

    def get_status(self) -> dict:
        return {
            "is_running": self._running,
            "interval": self.interval,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_error": self.last_error,
            "cycles": self.cycles,
            "trades_today": self.trades_today,
            "signals_last": self.signals_last,
            "orders_last": self.orders_last,
        }

    def _run_loop(self):
        while not self._stop_event.is_set():
            cycle_start = time.time()
            try:
                self._execute_cycle()
                self.cycles += 1
                self.last_run = datetime.now()
                self.last_error = ""
            except Exception as e:
                self.last_error = str(e)
                print(f"[AutoTrader] 错误: {e}")

            elapsed = time.time() - cycle_start
            sleep_time = max(0, self.interval - elapsed)
            self._stop_event.wait(sleep_time)

    def _execute_cycle(self):
        from app.trading.paper_engine import paper_engine
        from app.datasources.ths_hot_source import fetch_ths_hot
        from app.strategies.manager import strategy_manager
        from app.api.strategy import _enrich_prices
        from app.scanner.full_scanner import batch_tencent_quotes

        # 1. 取热点股票
        hot = fetch_ths_hot()
        if not hot:
            return

        # 2. 补充实时价格
        hot = _enrich_prices(hot)

        # 3. 跑全部策略
        signals = strategy_manager.run_all(hot)
        if not signals:
            return

        # 4. 构造信号字典 + 取行情
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

        # 5. 处理信号 → 执行交易
        orders = paper_engine.process_signals(signal_dicts, quotes)
        paper_engine.update_positions(quotes)

        self.signals_last = len(signal_dicts)
        self.orders_last = len(orders)

        if orders:
            self.trades_today += len(orders)
            orders_data = [
                {
                    "code": o.code, "name": o.name,
                    "direction": o.direction, "price": o.price,
                    "volume": o.volume, "strategy": o.strategy,
                    "reason": o.reason, "time": o.filled_at,
                }
                for o in orders
            ]
            print(f"[AutoTrader] 成交{len(orders)}笔: "
                  f"买入{sum(1 for o in orders if o.direction == 'buy')}/"
                  f"卖出{sum(1 for o in orders if o.direction == 'sell')} | "
                  f"总资产{paper_engine.total_value:,.0f}")

            if self._on_trade:
                self._on_trade(orders_data)

        # 6. 通知周期完成
        if self._on_cycle:
            self._on_cycle(self.get_status())


# 全局实例
auto_trader = AutoTrader(interval=5.0)
