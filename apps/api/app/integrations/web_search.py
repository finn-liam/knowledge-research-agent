"""Tavily 网页搜索：有 Key 走真实 API，无 Key 返回空列表由上层降级为模拟数据。"""
import httpx

from app.core.config import get_settings

settings = get_settings()

TAVILY_API = "https://api.tavily.com/search"


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    if not settings.tavily_enabled:
        return []
    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(TAVILY_API, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    results: list[dict] = []
    for item in data.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": (item.get("content") or "")[:260],
                "meta": {"score": item.get("score", 0.0)},
            }
        )
    return results
