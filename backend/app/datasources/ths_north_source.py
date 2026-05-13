import requests


def fetch_north_realtime() -> dict:
    url = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/north"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://hot.10jqka.com.cn/",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()

        if not data.get("data"):
            return {}

        north_data = data["data"]
        return {
            "hgt_yi": float(north_data.get("hgt", 0)),
            "sgt_yi": float(north_data.get("sgt", 0)),
            "total_yi": float(north_data.get("total", 0)),
            "updated_at": north_data.get("update_time", ""),
        }

    except Exception as e:
        return {}


def fetch_north_history() -> list[dict]:
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPT_MUTUAL_DEAL_HISTORY",
        "columns": "ALL",
        "pageSize": 30,
        "sortColumns": "TRADE_DATE",
        "sortTypes": "-1",
        "source": "WEB",
        "client": "WEB",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if not data.get("result", {}).get("data"):
            return []

        results = []
        for item in data["result"]["data"]:
            results.append({
                "date": item.get("TRADE_DATE", "")[:10],
                "time": "daily",
                "hgt_yi": round(float(item.get("MUTUAL_DEAL_NET", 0)) / 100000000, 2),
                "sgt_yi": round(float(item.get("DEAL_NET_SH", 0)) / 100000000, 2),
            })
        return results

    except Exception as e:
        return []
