"""
自动策略优化器 — 后台持续回测+自动调参
每5分钟拉取热点数据，对各策略进行回测，自动调优置信度阈值和止损止盈参数
"""
import time
import threading
from datetime import datetime
from typing import Optional


class AutoOptimizer:
    def __init__(self, interval: float = 300.0):
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self.last_run: Optional[datetime] = None
        self.last_error = ""
        self.cycles = 0
        self.optimizations: list[dict] = []

        # 策略参数调优空间
        self.param_grid = {
            "stop_loss_pct": [0.03, 0.05, 0.07],
            "take_profit_pct": [0.10, 0.15, 0.20],
            "confidence_min": [55, 60, 65, 70],
        }

        # 当前最优参数
        self.best_params: dict[str, dict] = {}

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="auto-optimizer")
        self._thread.start()
        print(f"[AutoOptimizer] 策略自动优化已启动 (间隔{self.interval}s)")

    def stop(self):
        self._running = False
        self._stop_event.set()

    def get_status(self) -> dict:
        return {
            "is_running": self._running,
            "interval": self.interval,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_error": self.last_error,
            "cycles": self.cycles,
            "optimization_count": len(self.optimizations),
            "latest_optimizations": self.optimizations[-10:],
            "best_params": self.best_params,
        }

    def _run_loop(self):
        # 首次延迟60秒，等系统初始化完成
        self._stop_event.wait(60)

        while not self._stop_event.is_set():
            cycle_start = time.time()
            try:
                self._execute_cycle()
                self.cycles += 1
                self.last_run = datetime.now()
                self.last_error = ""
            except Exception as e:
                self.last_error = str(e)
                print(f"[AutoOptimizer] 错误: {e}")

            elapsed = time.time() - cycle_start
            sleep_time = max(0, self.interval - elapsed)
            self._stop_event.wait(sleep_time)

    def _execute_cycle(self):
        from app.datasources.ths_hot_source import fetch_ths_hot
        from app.strategies.manager import strategy_manager
        from app.api.strategy import _enrich_prices
        from app.backtest.engine import backtest_engine
        from app.scanner.full_scanner import batch_tencent_quotes

        hot = fetch_ths_hot()
        if not hot:
            return

        hot = _enrich_prices(hot)

        for strategy in strategy_manager.strategies:
            signals = strategy_manager.run_strategy(strategy.name, hot)
            if len(signals) < 3:
                continue

            # 按置信度过滤
            best_overall = None
            best_params = None

            for sl in self.param_grid["stop_loss_pct"]:
                for tp in self.param_grid["take_profit_pct"]:
                    for conf_min in self.param_grid["confidence_min"]:
                        # 过滤低置信度信号
                        filtered = [s for s in signals if s.confidence >= conf_min]
                        if len(filtered) < 3:
                            continue

                        signal_dicts = [
                            {
                                "code": s.code, "name": s.name,
                                "price": s.price, "stop_loss": s.price * (1 - sl),
                                "target_price": s.price * (1 + tp),
                                "strategy": s.strategy, "reason": s.reason,
                            }
                            for s in filtered
                        ]

                        codes = list({s["code"] for s in signal_dicts})
                        quotes = batch_tencent_quotes(codes) if codes else {}

                        # 回测
                        result = backtest_engine.run(signal_dicts, {})

                        score = (
                            result.win_rate * 0.35
                            + max(0, result.sharpe_ratio) * 5 * 0.25
                            + max(0, result.total_return) * 0.25
                            - result.max_drawdown * 0.15
                        )

                        if best_overall is None or score > best_overall:
                            best_overall = score
                            best_params = {
                                "stop_loss_pct": sl,
                                "take_profit_pct": tp,
                                "confidence_min": conf_min,
                                "score": round(score, 2),
                                "win_rate": result.win_rate,
                                "total_return": result.total_return,
                                "sharpe_ratio": result.sharpe_ratio,
                                "max_drawdown": result.max_drawdown,
                                "total_trades": result.total_trades,
                            }

            if best_params:
                prev = self.best_params.get(strategy.name)
                if prev is None or best_params["score"] > prev.get("score", 0):
                    self.best_params[strategy.name] = best_params
                    self.optimizations.append({
                        "time": datetime.now().isoformat(),
                        "strategy": strategy.name,
                        **best_params,
                    })
                    print(f"[AutoOptimizer] {strategy.name}: "
                          f"sl={best_params['stop_loss_pct']:.0%} "
                          f"tp={best_params['take_profit_pct']:.0%} "
                          f"conf≥{best_params['confidence_min']} "
                          f"score={best_params['score']}")

        # 裁剪历史
        if len(self.optimizations) > 500:
            self.optimizations = self.optimizations[-200:]


auto_optimizer = AutoOptimizer(interval=300.0)
