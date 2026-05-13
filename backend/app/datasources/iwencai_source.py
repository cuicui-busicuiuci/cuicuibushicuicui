import os
import requests


def search_reports(query: str, size: int = 50) -> list[dict]:
    api_key = os.environ.get("IWENCAI_API_KEY")
    if not api_key:
        return []

    url = "https://openapi.iwencai.com/customized/v2/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "per_page": size,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        data = resp.json()

        if not data.get("data", {}).get("answer"):
            return []

        results = []
        for item in data["data"]["answer"][0].get("txt", [{}])[0].get("content", {}).get("components", []):
            for row in item.get("data", {}).get("datas", []):
                results.append({
                    "code": row.get("code", ""),
                    "name": row.get("name", ""),
                    "title": row.get("title", ""),
                    "source": "iwencai",
                })
        return results

    except Exception as e:
        return []
