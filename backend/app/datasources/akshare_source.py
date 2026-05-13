import akshare as ak
import time


def fetch_stock_news(code: str) -> list[dict]:
    try:
        df = ak.stock_news_em(symbol=code)
        if df is None or df.empty:
            return []

        results = []
        for _, row in df.head(20).iterrows():
            results.append({
                "code": code,
                "source": "eastmoney",
                "title": str(row.get("新闻标题", "")),
                "content": str(row.get("新闻内容", ""))[:500],
                "url": str(row.get("新闻链接", "")),
                "pub_time": str(row.get("发布时间", "")),
            })
        return results
    except Exception:
        return []


def fetch_cls_news(limit: int = 50) -> list[dict]:
    try:
        df = ak.stock_info_global_cls()
        if df is None or df.empty:
            return []

        results = []
        for _, row in df.head(limit).iterrows():
            results.append({
                "source": "cls",
                "title": str(row.get("标题", "")),
                "content": str(row.get("内容", ""))[:500],
                "pub_time": str(row.get("发布时间", "")),
            })
        return results
    except Exception:
        return []


def fetch_global_news(limit: int = 50) -> list[dict]:
    try:
        df = ak.stock_info_global_em()
        if df is None or df.empty:
            return []

        results = []
        for _, row in df.head(limit).iterrows():
            results.append({
                "source": "em_global",
                "title": str(row.get("标题", "")),
                "content": str(row.get("内容", ""))[:500],
                "pub_time": str(row.get("发布时间", "")),
            })
        return results
    except Exception:
        return []


def fetch_consensus_forecast(code: str) -> dict | None:
    try:
        df = ak.stock_profit_forecast_ths(symbol=code, indicator="预测年报每股收益")
        if df is None or df.empty:
            return None

        row = df.iloc[0]
        return {
            "code": code,
            "year": str(row.get("报告期", "")),
            "eps_mean": float(row.get("预测值", 0)),
            "analyst_count": int(row.get("机构数", 0)),
        }
    except Exception:
        return None


def fetch_stock_info(code: str) -> dict | None:
    try:
        df = ak.stock_individual_info_em(symbol=code)
        if df is None or df.empty:
            return None

        info = {}
        for _, row in df.iterrows():
            key = str(row.iloc[0])
            val = row.iloc[1]
            if "行业" in key:
                info["industry"] = str(val)
            elif "总股本" in key:
                info["total_share"] = float(val)
            elif "流通股" in key:
                info["float_share"] = float(val)
            elif "上市时间" in key:
                info["list_date"] = str(val)

        return info
    except Exception:
        return None
