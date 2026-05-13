import requests


def fetch_reports(code: str, size: int = 20) -> list[dict]:
    url = "https://reportapi.eastmoney.com/report/list"
    params = {
        "industryCode": "*",
        "pageSize": size,
        "industry": "*",
        "rating": "*",
        "ratingChange": "*",
        "beginTime": "",
        "endTime": "",
        "pageNo": 1,
        "fields": "",
        "qType": 0,
        "orgCode": "",
        "code": code,
        "rcode": "",
        "p": 1,
        "pageNum": 1,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if not data.get("data"):
            return []

        results = []
        for item in data["data"]:
            results.append({
                "info_code": item.get("infoCode", ""),
                "code": code,
                "title": item.get("title", ""),
                "publish_date": item.get("publishDate", "")[:10],
                "org_name": item.get("orgSName", ""),
                "rating": item.get("emRatingName", ""),
                "industry": item.get("industryName", ""),
                "predict_this_eps": item.get("predictThisYearEps"),
                "predict_next_eps": item.get("predictNextYearEps"),
                "predict_next2_eps": item.get("predictNextTwoYearEps"),
            })
        return results

    except Exception as e:
        return []
