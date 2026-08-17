"""LLM 网关：有 DEEPSEEK_API_KEY 走 DeepSeek(deepseek-v4-flash)，否则 Mock 模式。

Mock 模式产出模板化研究报告（含 [n] 引用）与模拟规划/图谱抽取，
保证无任何 Key 时演示链路完整可跑。
"""
import asyncio
import json
import re
from typing import Any, AsyncIterator

from app.core.config import get_settings

settings = get_settings()


def _extract_json(text: str) -> dict | list | None:
    """从 LLM 输出中稳健提取 JSON（容忍 markdown 代码块包裹）。"""
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidate = match.group(1) if match else text
    try:
        return json.loads(candidate.strip())
    except (json.JSONDecodeError, ValueError):
        return None


class LLMGateway:
    """统一 LLM 出口：report 流式生成 + 结构化 JSON 抽取。"""

    def __init__(self) -> None:
        self._chat = None
        if settings.llm_enabled:
            from langchain_openai import ChatOpenAI

            self._chat = ChatOpenAI(
                model=settings.deepseek_model,
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                temperature=0.3,
                streaming=True,
                max_retries=2,
            )

    @property
    def mode(self) -> str:
        return "deepseek" if self._chat else "mock"

    # ---------- 报告流式生成 ----------
    async def stream_report(self, prompt: str, mock_text: str) -> AsyncIterator[str]:
        if self._chat:
            try:
                # 超时兜底：LLM 流式中断/超时不会无限等待，降级用真实片段摘录补全
                # 注意：不能用 asyncio.wait_for 包 async generator（会 TypeError），
                # 必须用 asyncio.timeout 上下文管理器包裹迭代
                async with asyncio.timeout(240.0):
                    async for chunk in self._chat.astream(prompt):
                        if chunk.content:
                            yield str(chunk.content)
                return
            except Exception as exc:
                # 真实调用失败/超时 → 降级摘录补全（保证链路不中断），并记录原因
                print(f"[kra][llm] 真实 LLM 流式降级: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
        for piece in _chunk_text(mock_text):
            yield piece
            await asyncio.sleep(0.015)

    # ---------- 结构化抽取（规划 / 图谱） ----------
    async def extract_json(self, prompt: str, mock_payload: Any) -> Any:
        if self._chat:
            try:
                resp = await self._chat.ainvoke(prompt)
                parsed = _extract_json(str(resp.content))
                if parsed is not None:
                    return parsed
            except Exception:
                pass
        return mock_payload


def _chunk_text(text: str, size: int = 6) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


_gateway: LLMGateway | None = None


def get_llm() -> LLMGateway:
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
