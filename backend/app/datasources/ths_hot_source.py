import requests
from datetime import date as date_module


def fetch_ths_hot(date: str = None) -> list[dict]:
    url = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock"
    params = {
        "stock_type": "a",
        "type": "hour",
        "list_type": "normal",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://hot.10jqka.com.cn/",
    }

    if date is None:
        date = date_module.today().isoformat()

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()

        if not data.get("data", {}).get("stock_list"):
            return []

        results = []
        for item in data["data"]["stock_list"]:
            tag = item.get("tag", {})
            concept_tags = tag.get("concept_tag", [])
            popularity_tag = tag.get("popularity_tag", "")

            results.append({
                "date": date,
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "reason": item.get("analyse_title", ""),
                "analyse": item.get("analyse", ""),
                "change_pct": float(item.get("rise_and_fall", 0)),
                "hot_score": float(item.get("rate", 0)),
                "concept_tags": concept_tags,
                "popularity_tag": popularity_tag,
                "close_price": 0,
            })
        return results

    except Exception as e:
        print(f"同花顺热点获取失败: {e}")
        return []
