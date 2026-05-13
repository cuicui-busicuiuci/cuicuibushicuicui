"""
技术指标评分模块
基于腾讯行情数据计算多维度技术评分，无需依赖mootdx K线
所有计算基于实时快照数据（价格/涨跌幅/换手率/量比/振幅/PE/PB等）
"""


def calc_tech_score(stock: dict) -> dict:
    """
    计算单只股票的技术面综合评分 (0-100)
    返回评分详情，包含各维度得分和信号
    """
    price = stock.get("price", 0)
    open_p = stock.get("open", 0)
    high = stock.get("high", 0)
    low = stock.get("low", 0)
    last_close = stock.get("last_close", 0)
    change_pct = stock.get("change_pct", 0)
    turnover_pct = stock.get("turnover_pct", 0)
    vol_ratio = stock.get("vol_ratio", 0)
    amplitude = stock.get("amplitude_pct", 0)
    pe_ttm = stock.get("pe_ttm", 0)
    pb = stock.get("pb", 0)
    mcap = stock.get("mcap_yi", 0)
    limit_up = stock.get("limit_up", 0)
    limit_down = stock.get("limit_down", 0)

    if not price or price <= 0:
        return {"total_score": 0, "details": [], "signals": []}

    scores = {}
    signals = []
    details = []

    # 1. 趋势强度 (0-25分)
    if change_pct >= 9.5:
        trend_score = 25
        signals.append("涨停封板")
        details.append(f"涨停+{change_pct:.1f}%")
    elif change_pct >= 7:
        trend_score = 22
        signals.append("强势拉升")
    elif change_pct >= 5:
        trend_score = 18
        signals.append("稳步上涨")
    elif change_pct >= 3:
        trend_score = 14
    elif change_pct >= 1:
        trend_score = 10
    elif change_pct > 0:
        trend_score = 6
    elif change_pct >= -1:
        trend_score = 3
    elif change_pct >= -3:
        trend_score = 1
    else:
        trend_score = 0
    scores["趋势"] = trend_score
    if change_pct:
        details.append(f"涨跌{change_pct:+.1f}%")

    # 2. 振幅健康度 (0-15分) — 有振幅才有交易机会
    if amplitude and amplitude > 0:
        if 3 <= amplitude <= 8:
            amp_score = 15
            details.append(f"振幅{amplitude:.1f}%(健康)")
        elif 8 < amplitude <= 12:
            amp_score = 10
            details.append(f"振幅{amplitude:.1f}%(偏高)")
        elif 2 <= amplitude < 3:
            amp_score = 8
            details.append(f"振幅{amplitude:.1f}%(偏低)")
        elif amplitude > 12:
            amp_score = 4
            details.append(f"振幅{amplitude:.1f}%(过大)")
        else:
            amp_score = 3
        scores["振幅"] = amp_score

    # 3. 量能活跃度 (0-20分)
    vol_score = 0
    if vol_ratio and vol_ratio > 0:
        if vol_ratio >= 3:
            vol_score = 20
            signals.append("放量3倍")
            details.append(f"量比{vol_ratio:.1f}(巨量)")
        elif vol_ratio >= 2:
            vol_score = 18
            signals.append("放量2倍")
        elif vol_ratio >= 1.5:
            vol_score = 15
            details.append(f"量比{vol_ratio:.1f}(放量)")
        elif vol_ratio >= 1.0:
            vol_score = 12
        elif vol_ratio >= 0.8:
            vol_score = 8
        elif vol_ratio >= 0.5:
            vol_score = 5
        else:
            vol_score = 2
    elif turnover_pct and turnover_pct > 0:
        if turnover_pct >= 20:
            vol_score = 18
            signals.append("超高换手")
        elif turnover_pct >= 10:
            vol_score = 15
            signals.append("活跃换手")
            details.append(f"换手{turnover_pct:.1f}%")
        elif turnover_pct >= 5:
            vol_score = 12
            details.append(f"换手{turnover_pct:.1f}%")
        elif turnover_pct >= 2:
            vol_score = 8
        elif turnover_pct >= 1:
            vol_score = 5
        else:
            vol_score = 2
    scores["量能"] = vol_score

    # 4. 价格形态 (0-15分) — K线实体与影线
    if high and low and last_close and price and open_p:
        candle_range = high - low
        if candle_range > 0:
            body = abs(price - open_p)
            upper_shadow = high - max(price, open_p)
            lower_shadow = min(price, open_p) - low
            body_pct = body / candle_range if candle_range > 0 else 0
            upper_pct = upper_shadow / candle_range if candle_range > 0 else 0
            lower_pct = lower_shadow / candle_range if candle_range > 0 else 0

            form_score = 8  # base
            # 阳线实体大 → 强
            if price > open_p and body_pct > 0.5:
                form_score += 4
                details.append("实体阳线")
            # 下影线长 → 支撑强
            if lower_pct > 0.3 and lower_shadow > 0:
                form_score += 3
                details.append("下影支撑")
            # 上影线过长 → 压力
            if upper_pct > 0.5 and change_pct < 3:
                form_score -= 3
                details.append("上影压力")
            scores["形态"] = max(0, min(15, form_score))

    # 5. 估值合理性 (0-15分)
    val_score = 8
    if pe_ttm and pe_ttm > 0:
        if 10 <= pe_ttm <= 30:
            val_score = 15
            details.append(f"PE{pe_ttm:.0f}(合理)")
        elif 30 < pe_ttm <= 60:
            val_score = 12
        elif 60 < pe_ttm <= 100:
            val_score = 8
        elif 0 < pe_ttm < 10:
            val_score = 6
        elif pe_ttm > 100:
            val_score = 3
        else:
            val_score = 8
    if pb and 0 < pb < 8:
        val_score = min(15, val_score + 2)
    scores["估值"] = val_score

    # 6. 市值因子 (0-10分) — 小市值溢价
    if mcap and mcap > 0:
        if mcap < 50:
            mcap_score = 10
        elif mcap < 100:
            mcap_score = 9
        elif mcap < 200:
            mcap_score = 7
        elif mcap < 500:
            mcap_score = 5
        elif mcap < 1000:
            mcap_score = 3
        else:
            mcap_score = 1
        scores["市值"] = mcap_score
        details.append(f"市值{mcap:.0f}亿")

    # 综合评分
    total = sum(scores.values())
    # 归一化到0-100
    max_possible = sum(v for k, v in {
        "趋势": 25, "振幅": 15, "量能": 20, "形态": 15, "估值": 15, "市值": 10
    }.items() if k in scores)
    if max_possible > 0:
        total = round(total / max_possible * 100)

    return {
        "total_score": min(100, total),
        "dimensions": scores,
        "signals": signals,
        "details": details,
    }
