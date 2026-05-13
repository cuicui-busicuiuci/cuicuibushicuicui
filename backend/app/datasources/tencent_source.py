import requests


def fetch_tencent_quote(code: str) -> dict | None:
    market = "sh" if code.startswith(("6", "9")) else "sz"
    url = f"https://qt.gtimg.cn/q={market}{code}"

    try:
        resp = requests.get(url, timeout=5)
        resp.encoding = "gbk"
        text = resp.text.strip()

        if "=" not in text:
            return None

        content = text.split("=")[1].strip('";\n')
        parts = content.split("~")

        if len(parts) < 50:
            return None

        def safe_float(val, default=0):
            try:
                return float(val) if val else default
            except (ValueError, TypeError):
                return default

        return {
            "code": code,
            "name": parts[1],
            "price": safe_float(parts[3]),
            "last_close": safe_float(parts[4]),
            "open": safe_float(parts[5]),
            "volume": safe_float(parts[6]),
            "amount": safe_float(parts[37]),
            "high": safe_float(parts[33]),
            "low": safe_float(parts[34]),
            "change_amt": safe_float(parts[31]),
            "change_pct": safe_float(parts[32]),
            "turnover_pct": safe_float(parts[38]),
            "pe_ttm": safe_float(parts[39]),
            "pb": safe_float(parts[46]),
            "mcap_yi": round(safe_float(parts[45]) / 10000, 2),
            "limit_up": safe_float(parts[47]),
            "limit_down": safe_float(parts[48]),
        }
    except Exception as e:
        print(f"腾讯行情获取失败 {code}: {e}")
        return None
