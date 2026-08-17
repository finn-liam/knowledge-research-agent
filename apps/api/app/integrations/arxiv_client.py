"""arXiv 论文检索（免费公开 API，无需 Key）；失败时返回空列表由上层降级。"""
import re
import xml.etree.ElementTree as ET

import httpx

ARXIV_API = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"


async def search_papers(query: str, max_results: int = 5) -> list[dict]:
    # arXiv 对英文检索友好；中文查询退化为关键词英文映射失败时也能容错
    q = re.sub(r"\s+", " ", query).strip() or "artificial intelligence"
    params = {
        "search_query": f"all:{q}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(ARXIV_API, params=params)
            resp.raise_for_status()
    except Exception:
        return []

    results: list[dict] = []
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return []

    for entry in root.findall(f"{ATOM}entry"):
        title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
        summary = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
        link = entry.findtext(f"{ATOM}id") or ""
        published = (entry.findtext(f"{ATOM}published") or "")[:10]
        arxiv_id = link.rsplit("/", 1)[-1] if link else ""
        if not title:
            continue
        results.append(
            {
                "title": f"arXiv:{arxiv_id} {title}" if arxiv_id else title,
                "url": link,
                "snippet": summary[:260],
                "meta": {"published": published, "arxiv_id": arxiv_id},
            }
        )
    return results
