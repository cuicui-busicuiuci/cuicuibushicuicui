"""硅基流动 AI 服务 — OpenAI兼容格式，支持DeepSeek-V3/Qwen3等30+模型"""
import os, json, time, requests
from datetime import datetime
from app.log_config import get_logger

logger = get_logger(__name__)


class AIService:
    """硅基流动 LLM 统一调用封装（带重试+退避+超时优化）"""

    BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
    MODEL = "deepseek-ai/DeepSeek-V3.2"       # 免费最强：最新DeepSeek V3
    MODEL_FAST = "Qwen/Qwen3-8B"              # 免费快速：轻量Qwen
    MODEL_CHEAP = "Qwen/Qwen3-8B"             # 兜底：同上
    MAX_TOKENS = 600
    TEMPERATURE = 0.7
    TIMEOUT = 300  # 300秒超时，最大化AI生成成功率（DeepSeek-V3正常5-15s，复杂分析可能更久）
    MAX_RETRIES = 3  # 增加重试次数

    def __init__(self):
        self.api_key = os.getenv("SILICONFLOW_API_KEY", "")
        self.call_count = 0
        self.fail_count = 0

    def _call(self, messages: list, model: str = None, max_tokens: int = None,
              temperature: float = None, timeout: int = None) -> str:
        """底层调用，带重试+退避，返回文本或空字符串"""
        if not self.api_key:
            return ""

        model = model or self.MODEL_FAST  # 默认用快速模型
        timeout = timeout or self.TIMEOUT
        max_tokens = max_tokens or self.MAX_TOKENS
        temperature = temperature or self.TEMPERATURE

        # 估算输入token数（中文字符约1.5token/字），超过2000token换便宜模型
        input_chars = sum(len(m.get("content", "")) for m in messages)
        if input_chars > 4000 and model == self.MODEL_FAST:
            model = self.MODEL  # 大prompt用DeepSeek-V3

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": min(max_tokens, 800),  # 限制输出token避免超时
            "temperature": temperature,
            "stream": False,
        }

        last_error = ""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                t0 = time.time()
                r = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=timeout)
                elapsed = time.time() - t0

                if r.status_code == 200:
                    data = r.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    self.call_count += 1
                    if attempt > 0:
                        logger.info(f"[AI] 重试{attempt}次后成功 ({elapsed:.1f}s)")
                    return content

                elif r.status_code == 429:
                    # 限流，退避重试
                    wait = 2 ** attempt
                    logger.warning(f"[AI] 限流429，{wait}s后重试...")
                    time.sleep(wait)
                    last_error = f"429 rate limit"
                    continue

                elif r.status_code == 503 or r.status_code >= 500:
                    wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                    logger.warning(f"[AI] 服务端{r.status_code}，{wait}s后重试...")
                    time.sleep(wait)
                    last_error = f"{r.status_code} server error"
                    if attempt >= 1 and model != self.MODEL_CHEAP:
                        model = self.MODEL_CHEAP
                        payload["model"] = model
                    continue

                else:
                    logger.warning(f"[AI] API错误{r.status_code}: {r.text[:150]}")
                    self.fail_count += 1
                    return ""

            except requests.Timeout:
                if attempt < self.MAX_RETRIES:
                    wait = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                    logger.warning(f"[AI] 超时({timeout}s)，{wait}s后重试({attempt+1}/{self.MAX_RETRIES})...")
                    time.sleep(wait)
                    # 第一次重试就切小模型，减少token量
                    if attempt >= 1 and model != self.MODEL_CHEAP:
                        model = self.MODEL_CHEAP
                        payload["model"] = model
                        max_tokens = min(max_tokens, 300)
                        payload["max_tokens"] = max_tokens
                        logger.info(f"[AI] 切换到快速模型，max_tokens={max_tokens}")
                    continue
                logger.warning(f"[AI] 超时({timeout}s)，已重试{self.MAX_RETRIES}次")
                self.fail_count += 1
                return ""

            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    logger.warning(f"[AI] 异常: {e}，重试...")
                    time.sleep(1)
                    continue
                logger.exception(f"[AI] 异常: {e}")
                self.fail_count += 1
                return ""

        logger.exception(f"[AI] 全部重试失败: {last_error}")
        self.fail_count += 1
        return ""

    def stats(self) -> dict:
        return {"calls": self.call_count, "fails": self.fail_count,
                "success_rate": f"{self.call_count/max(self.call_count+self.fail_count,1)*100:.0f}%"}

    def buy_reason(self, code: str, name: str, price: float, change_pct: float,
                   turnover_pct: float, pe_ttm: float, alpha_score: int,
                   tech_score: int, extra_context: str = "") -> str:
        """生成AI买入原因分析

        Args:
            extra_context: 额外上下文（资金流/机构行为/板块/技术指标等），拼接到prompt
        """
        extra_line = f"\n{extra_context}" if extra_context else ""
        prompt = f"""你是A股量化分析师。请针对以下股票数据，用2-3句话分析买入原因（50字以内，直接说结论，不要格式化）：

股票：{code} {name}
现价：{price}元 | 涨跌幅：{change_pct:+.1f}%
换手率：{turnover_pct:.1f}% | PE(TTM)：{pe_ttm:.1f}倍
Alpha综合评分：{alpha_score}/100 | 技术评分：{tech_score}/100{extra_line}

分析买入原因："""

        messages = [
            {"role": "system", "content": "你是A股量化分析师。回答简洁专业，每句不超过30字，不说废话。"},
            {"role": "user", "content": prompt},
        ]
        result = self._call(messages, model=self.MODEL_FAST, max_tokens=150, temperature=0.6)
        return result if result else self._fallback_buy_reason(alpha_score, tech_score, change_pct, turnover_pct)

    def risk_analysis(self, code: str, name: str, change_pct: float,
                      pe_ttm: float, turnover_pct: float, risk_level: str,
                      risk_factors: list, extra_context: str = "") -> str:
        """生成AI风险分析

        Args:
            extra_context: 额外上下文（资金流/机构行为等），拼接到prompt
        """
        factors_text = "、".join(risk_factors[:5]) if risk_factors else "无明显风险"
        extra_line = f"\n{extra_context}" if extra_context else ""
        prompt = f"""你是A股风控专家。针对以下股票数据给出风险建议（2-3句，80字以内）：

股票：{code} {name} | 涨跌{change_pct:+.1f}% | PE{pe_ttm:.1f} | 换手{turnover_pct:.1f}%
风险等级：{risk_level} | 风险因素：{factors_text}{extra_line}

风险建议："""

        messages = [
            {"role": "system", "content": "你是A股风控专家。回答简洁实用，直接给可执行的建议。"},
            {"role": "user", "content": prompt},
        ]
        result = self._call(messages, model=self.MODEL_FAST, max_tokens=150, temperature=0.5)
        return result if result else self._fallback_risk(risk_level, risk_factors)

    def review_summary(self, diagnostic_score: int, verdict: str, win_rate: float,
                       total_trades: int, sentiment_stage: str, sentiment_change: str,
                       risk_items: list) -> str:
        """生成AI复盘总结"""
        risks_text = "；".join(risk_items[:3]) if risk_items else "无特殊风险"
        prompt = f"""你是A股量化基金经理。请写一份今日复盘总结（3-4句，100字以内）：

诊断评分：{diagnostic_score}/100 | {verdict}
整体胜率：{win_rate:.0f}% | 总交易：{total_trades}笔
情绪阶段：{sentiment_stage} | 情绪变化：{sentiment_change}
风险提示：{risks_text}

复盘总结："""

        messages = [
            {"role": "system", "content": "你是量化基金经理。复盘总结专业但不啰嗦，直接说重点。"},
            {"role": "user", "content": prompt},
        ]
        result = self._call(messages, model=self.MODEL, max_tokens=200, temperature=0.7)
        return result if result else self._fallback_review(diagnostic_score, verdict, sentiment_change)

    def strategy_reason(self, strategy_name: str, code: str, name: str,
                        reason: str, confidence: int) -> str:
        """生成策略信号的AI增强解释"""
        prompt = f"""你是A股策略分析师。用一句话（30字内）解释为什么{strategy_name}策略对{code} {name}发出信号：
原始信号原因：{reason} | 置信度：{confidence}/100

增强解释："""

        messages = [
            {"role": "system", "content": "你是策略分析师。用一句话解释信号，不超过30字。"},
            {"role": "user", "content": prompt},
        ]
        result = self._call(messages, model=self.MODEL_FAST, max_tokens=80, temperature=0.5)
        return result if result else reason

    # ---- 规则兜底（API不可用时） ----

    def _fallback_buy_reason(self, alpha: int, tech: int, change: float, turnover: float) -> str:
        parts = []
        if alpha >= 80:
            parts.append(f"Alpha综合{alpha}分，多因子共振买入信号强烈")
        elif alpha >= 60:
            parts.append(f"Alpha评分{alpha}分，多因子偏向正面")
        if tech >= 70:
            parts.append(f"技术面{tech}分，量价形态健康")
        if change > 3:
            parts.append(f"涨幅{change:.1f}%，资金主动买入意愿强")
        if 3 <= turnover <= 15:
            parts.append(f"换手率{turnover:.1f}%处于活跃区间")
        return "；".join(parts) if parts else "暂无明确买入信号"

    def _fallback_risk(self, level: str, factors: list) -> str:
        if level == "HIGH":
            return f"风险较高，注意{'、'.join(factors[:2]) if factors else '仓位控制'}"
        elif level == "MEDIUM":
            return "风险可控，建议设好止损位，关注盘中变化"
        return "风险较低，可按计划操作"

    def _fallback_review(self, score: int, verdict: str, change: str) -> str:
        parts = [verdict] if verdict else []
        if change:
            parts.append(change)
        if score < 50:
            parts.append("建议降低仓位，等待信号改善")
        elif score >= 70:
            parts.append("系统运行良好，可继续执行现有策略")
        return "。".join(parts) + "。" if parts else "今日系统运行正常。"


# 全局实例
ai_service = AIService()
