import time
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request


_stock_list_cache: Optional[List[Dict]] = None
_stock_list_time = 0


def get_all_stocks() -> List[Dict]:
    """获取全A股股票代码列表（缓存1天，akshare）"""
    global _stock_list_cache, _stock_list_time
    now = time.time()
    if _stock_list_cache and (now - _stock_list_time) < 86400:
        return _stock_list_cache

    stocks = []
    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                code = str(row.get("code", ""))
                name = str(row.get("name", ""))
                if not code or len(code) != 6:
                    continue
                stocks.append({"code": code, "name": name, "price": 0, "change_pct": 0,
                               "volume": 0, "amount": 0, "turnover_pct": 0,
                               "pe_ttm": 0, "mcap": 0})
            _stock_list_cache = stocks
            _stock_list_time = now
            print(f"[扫描器] akshare获取到 {len(stocks)} 只A股代码")
    except Exception as e:
        print(f"[扫描器] akshare失败: {e}")

    return stocks or []


def batch_tencent_quotes(codes: List[str]) -> Dict[str, dict]:
    """批量获取腾讯实时行情（最多50只）"""
    prefixed = []
    for c in codes:
        if c.startswith(("6", "9")):
            prefixed.append(f"sh{c}")
        elif c.startswith("8"):
            prefixed.append(f"bj{c}")
        else:
            prefixed.append(f"sz{c}")

    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")

    result = {}
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read().decode("gbk")
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            key = line.split("=")[0].split("_")[-1]
            vals = line.split('"')[1].split("~")
            if len(vals) < 53:
                continue
            code = key[2:]
            result[code] = {
                "name": vals[1],
                "price": float(vals[3]) if vals[3] else 0,
                "last_close": float(vals[4]) if vals[4] else 0,
                "open": float(vals[5]) if vals[5] else 0,
                "change_amt": float(vals[31]) if vals[31] else 0,
                "change_pct": float(vals[32]) if vals[32] else 0,
                "high": float(vals[33]) if vals[33] else 0,
                "low": float(vals[34]) if vals[34] else 0,
                "amount_wan": float(vals[37]) if vals[37] else 0,
                "turnover_pct": float(vals[38]) if vals[38] else 0,
                "pe_ttm": float(vals[39]) if vals[39] else 0,
                "amplitude_pct": float(vals[43]) if vals[43] else 0,
                "mcap_yi": float(vals[44]) if vals[44] else 0,
                "float_mcap_yi": float(vals[45]) if vals[45] else 0,
                "pb": float(vals[46]) if vals[46] else 0,
                "limit_up": float(vals[47]) if vals[47] else 0,
                "limit_down": float(vals[48]) if vals[48] else 0,
                "vol_ratio": float(vals[49]) if vals[49] else 0,
            }
    except Exception as e:
        print(f"[扫描器] 腾讯批量行情失败: {e}")

    return result


def pre_filter(stocks: List[Dict]) -> List[Dict]:
    """预筛选：排除ST/退市/北交所/B股"""
    filtered = []
    for s in stocks:
        name = s.get("name", "")
        code = s.get("code", "")
        if not code or not name:
            continue
        if "ST" in name or "退市" in name:
            continue
        if code.startswith("8") or code.startswith("9"):
            continue
        filtered.append(s)
    return filtered


def enrich_with_quotes(stocks: List[Dict], max_workers: int = 10) -> List[Dict]:
    """批量获取实时行情并填充到股票数据中"""
    batch_size = 50
    enriched = []

    def fetch_batch(batch_codes):
        quotes = batch_tencent_quotes(batch_codes)
        batch_result = []
        for s in batch_codes:
            code = s if isinstance(s, str) else s["code"]
            q = quotes.get(code, {})
            if q:
                entry = {
                    "code": code,
                    "name": q.get("name", s["name"] if not isinstance(s, str) else ""),
                    "price": q.get("price", 0),
                    "last_close": q.get("last_close", 0),
                    "change_pct": q.get("change_pct", 0),
                    "open": q.get("open", 0),
                    "high": q.get("high", 0),
                    "low": q.get("low", 0),
                    "volume": q.get("amount_wan", 0),
                    "turnover_pct": q.get("turnover_pct", 0),
                    "vol_ratio": q.get("vol_ratio", 0),
                    "amplitude_pct": q.get("amplitude_pct", 0),
                    "pe_ttm": q.get("pe_ttm", 0),
                    "mcap": q.get("mcap_yi", 0),
                    "mcap_yi": q.get("mcap_yi", 0),
                    "pb": q.get("pb", 0),
                    "limit_up": q.get("limit_up", 0),
                    "limit_down": q.get("limit_down", 0),
                }
                batch_result.append(entry)
        return batch_result

    codes = [s["code"] for s in stocks]
    batches = [codes[i:i + batch_size] for i in range(0, len(codes), batch_size)]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_batch, b): b for b in batches}
        for i, future in enumerate(as_completed(futures)):
            try:
                enriched.extend(future.result(timeout=15))
            except Exception as e:
                print(f"[扫描器] 批次失败: {e}")
            if (i + 1) % 20 == 0:
                print(f"[扫描器] 行情获取进度: {i+1}/{len(batches)} 批")

    return enriched


def scan_stock(stock: dict, strategy_manager, sentiment_model) -> dict:
    """对单只股票进行全策略扫描 + 技术指标评分"""
    try:
        code = stock["code"]
        name = stock["name"]
        price = stock.get("price", 0)
        change_pct = stock.get("change_pct", 0)
        mcap = stock.get("mcap", 0)
        turnover = stock.get("turnover_pct", 0)

        if not price or price <= 0:
            return None

        # 技术面评分
        from app.scanner.tech_score import calc_tech_score
        tech = calc_tech_score(stock)

        data = {
            "code": code, "name": name,
            "price": price, "close_price": price,
            "change_pct": change_pct,
            "hot_score": stock.get("volume", 0),
            "concept_tags": [],
            "popularity_tag": "",
            "reason": f"全A扫描 | 涨幅{change_pct:+.2f}% | 换手{turnover:.1f}% | PE{stock.get('pe_ttm',0):.0f} | 技术{tech['total_score']}分",
            "analyse": "",
        }

        signals = []
        for strategy in strategy_manager.strategies:
            try:
                sig = strategy.check_conditions(data)
                if sig:
                    signals.append({
                        "strategy": sig.strategy,
                        "confidence": sig.confidence,
                        "reason": sig.reason[:60],
                        "stop_loss": sig.stop_loss,
                        "target_price": sig.target_price,
                    })
            except Exception:
                pass

        # 技术分不够且无策略信号则跳过
        if not signals and tech["total_score"] < 40:
            return None

        # 综合评分 = 策略信心度(60%) + 技术面(40%)
        if signals:
            avg_confidence = sum(s["confidence"] for s in signals) / len(signals)
            strategy_bonus = min(len(signals) * 3, 15)
            composite = round(avg_confidence * 0.5 + tech["total_score"] * 0.35 + strategy_bonus, 1)
        else:
            avg_confidence = 0
            composite = round(tech["total_score"] * 0.8, 1)

        return {
            "code": code,
            "name": name,
            "price": price,
            "change_pct": change_pct,
            "mcap": mcap,
            "turnover_pct": turnover,
            "pe_ttm": stock.get("pe_ttm", 0),
            "pb": stock.get("pb", 0),
            "signals": signals,
            "signal_count": len(signals),
            "avg_confidence": round(avg_confidence, 1),
            "composite_score": composite,
            "tech_score": tech["total_score"],
            "tech_signals": tech.get("signals", []),
            "tech_details": tech.get("details", []),
            "strategies": list(set(s["strategy"] for s in signals)),
        }
    except Exception:
        return None


def full_market_scan(max_stocks: int = 0, min_score: int = 40, with_quotes: bool = True) -> dict:
    """
    全市场扫描
    max_stocks: 0=全部, >0=限制数量
    min_score: 最低综合分数阈值
    with_quotes: 是否获取实时行情
    """
    from app.strategies.manager import strategy_manager

    start = time.time()
    all_stocks = get_all_stocks()
    if not all_stocks:
        return {"error": "无法获取股票列表", "count": 0, "results": []}

    candidates = pre_filter(all_stocks)
    print(f"[扫描器] 预筛选后: {len(candidates)}/{len(all_stocks)} 只")

    if with_quotes:
        print(f"[扫描器] 开始批量获取实时行情...")
        candidates = enrich_with_quotes(candidates)
        print(f"[扫描器] 获取到 {len(candidates)} 只有效行情")
        # 再次用实时数据筛选
        candidates = [s for s in candidates if s.get("price", 0) >= 2 and s.get("turnover_pct", 0) > 0]

    if max_stocks and max_stocks > 0:
        candidates = candidates[:max_stocks]

    results = []
    workers = min(20, max(1, len(candidates) // 100))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(scan_stock, s, strategy_manager, None): s for s in candidates}
        for i, future in enumerate(as_completed(futures)):
            try:
                r = future.result(timeout=10)
                if r and r["composite_score"] >= min_score:
                    results.append(r)
            except Exception:
                pass
            if (i + 1) % 500 == 0:
                print(f"[扫描器] 策略扫描进度: {i+1}/{len(candidates)}")

    results.sort(key=lambda x: x["composite_score"], reverse=True)

    elapsed = time.time() - start
    print(f"[扫描器] 扫描完成: {len(results)} 只入选, 耗时 {elapsed:.1f}s")

    scan_data = {
        "timestamp": datetime.now().isoformat(),
        "total_scanned": len(candidates),
        "total_universe": len(all_stocks),
        "results_count": len(results),
        "scan_time_seconds": round(elapsed, 1),
        "results": results[:200],
        "top_strategies": _summarize_strategies(results),
    }

    # 自动持久化
    try:
        from app.db.persistence import save_scan_session
        session_id = save_scan_session(scan_data)
        print(f"[扫描器] 结果已保存, session_id={session_id}")
    except Exception as e:
        print(f"[扫描器] 持久化失败: {e}")

    return scan_data


def _summarize_strategies(results: List[dict]) -> dict:
    from collections import Counter
    counter = Counter()
    for r in results:
        for s in r.get("signals", []):
            counter[s["strategy"]] += 1
    return dict(counter.most_common(10))
