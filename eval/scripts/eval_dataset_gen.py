"""Golden Dataset 生成 v2：文档加权抽样 + 三类题型（事实/图表/综合分析）+ 多切片标注。

用法：python eval/scripts/eval_dataset_gen.py [总条数，默认 35]
输出：eval/dataset.json（覆盖全部文档，含 Hello-Agents / RealityCapture 图表题）
"""
import asyncio
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # knowledge-research-agent
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.llm.gateway import get_llm  # noqa: E402
from app.models.research import Document, DocumentChunk  # noqa: E402

# 每文档目标题数（按文档名前缀分配，合计≈总条数）
FACT_PROMPT = """你是企业知识库数据标注员。请基于以下文档片段生成一条知识问答数据。

【片段内容】
{chunk_text}

【输出要求】输出 JSON（不要输出其他内容）：
{{
  "question": "基于该片段提出的自然中文问题（信息完整、可独立回答）",
  "ground_truth": "标准答案（严格基于片段内容，2-4 句）"
}}
"""

CHART_PROMPT = """你是企业知识库数据标注员。以下片段包含对文档中【图片/图表/界面截图】的描述（OCR 或 VLM 生成）。

【片段内容】
{chunk_text}

【输出要求】输出 JSON（不要输出其他内容）：
{{
  "question": "基于图中内容提出的问题（如数据趋势、界面功能、图表结论，信息完整可独立回答）",
  "ground_truth": "标准答案（严格基于图片描述内容，2-4 句）"
}}
"""

ANALYSIS_PROMPT = """你是企业知识库数据标注员。以下是一份文档的【章节级完整内容】（含多个段落与小节）。

【章节内容】
{chunk_text}

【输出要求】输出 JSON（不要输出其他内容）：
{{
  "question": "基于整个章节内容提出的综合性分析问题（需要综合多个要点回答）",
  "ground_truth": "综合答案（覆盖章节核心要点，3-5 句）"
}}
"""


def doc_group(name: str) -> str:
    if name.startswith("Hello-Agents"):
        return "hello"
    if name.startswith("RealityCapture"):
        return "reality"
    if name == "bigdata-ai.docx":
        return "bigdata"
    return name.split("_")[0]  # chapterN


async def main() -> int:
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    llm = get_llm()

    async with SessionLocal() as db:
        docs = {d.id: d for d in (await db.execute(select(Document))).scalars().all()}
        chunks = (
            await db.execute(
                select(DocumentChunk).order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
            )
        ).scalars().all()

    by_doc: dict[int, list[DocumentChunk]] = {}
    for c in chunks:
        by_doc.setdefault(c.document_id, []).append(c)

    # 文档加权分配：每文档目标条数
    group_targets = {"hello": 10, "reality": 7, "bigdata": 2}
    chapter_targets = {
        "chapter1": 2, "chapter2": 2, "chapter3": 2, "chapter4": 2,
        "chapter5": 1, "chapter6": 1, "chapter7": 1, "chapter8": 2, "chapter9": 2,
    }
    doc_targets: dict[int, int] = {}
    for doc_id, doc in docs.items():
        g = doc_group(doc.name)
        if g in group_targets:
            doc_targets[doc_id] = group_targets[g]
        elif g in chapter_targets:
            doc_targets[doc_id] = chapter_targets[g]
        else:
            doc_targets[doc_id] = 1

    # 加权分配：每个文档至少 1 条，剩余额度按目标权重抽样，总数精确 = total
    random.seed(42)
    doc_ids = [did for did in doc_targets if by_doc.get(did)]
    weights = [doc_targets[did] for did in doc_ids]

    def pick_chunk(did: int) -> DocumentChunk:
        """hello/reality 组优先选含图描述切片（提高图表题产出）。"""
        cs = by_doc[did]
        group = doc_group(docs[did].name) if did in docs else ""
        if group in ("hello", "reality"):
            chart_cs = [c for c in cs if "图描述" in c.text or "[图]" in c.text]
            if chart_cs and random.random() < 0.7:
                return random.choice(chart_cs)
        return random.choice(cs)

    sampled_pool = [pick_chunk(did) for did in doc_ids]  # 每文档 1 条
    rest = total - len(sampled_pool)
    for _ in range(max(0, rest)):
        did = random.choices(doc_ids, weights=weights, k=1)[0]
        sampled_pool.append(pick_chunk(did))
    random.shuffle(sampled_pool)
    sampled_pool = sampled_pool[:total]

    items = []
    for i, c in enumerate(sampled_pool):
        doc = docs.get(c.document_id)
        name = doc.name if doc else f"doc{c.document_id}"
        text = c.text
        is_chart = ("[图" in text) and ("图描述" in text or "[图]" in text)
        # 综合分析题：用 parent 章节文本（约 1/4 概率，且非图表题）
        use_parent = (not is_chart) and (i % 4 == 0) and bool(c.parent_text)
        prompt_text = c.parent_text[:3000] if use_parent else text[:1200]

        if is_chart:
            prompt = CHART_PROMPT.format(chunk_text=prompt_text)
            mock = {"question": f"图中显示了什么数据或结构？", "ground_truth": text[:120]}
        elif use_parent:
            prompt = ANALYSIS_PROMPT.format(chunk_text=prompt_text)
            mock = {"question": "该章节的核心内容与要点是什么？", "ground_truth": c.parent_text[:150]}
        else:
            prompt = FACT_PROMPT.format(chunk_text=prompt_text)
            mock = {"question": f"片段{c.document_id}#{c.chunk_index} 内容是什么？",
                    "ground_truth": text[:120]}

        payload = await llm.extract_json(prompt, mock)
        question = (payload.get("question") or "").strip()
        answer = (payload.get("ground_truth") or "").strip()
        if not question or not answer:
            continue

        # 多切片标注：本切片 + 同文档相邻切片
        relevant = [f"{c.document_id}#{c.chunk_index}"]
        siblings = by_doc.get(c.document_id, [])
        for sib in siblings:
            if abs(sib.chunk_index - c.chunk_index) == 1:
                relevant.append(f"{c.document_id}#{sib.chunk_index}")
        items.append({
            "id": f"q{i+1:02d}",
            "question": question,
            "ground_truth": answer,
            "relevant_chunks": relevant,
            "doc_name": name,
            "type": "chart" if is_chart else ("analysis" if use_parent else "fact"),
        })
        print(f"[gen] {items[-1]['id']} [{items[-1]['type']}] | {name[:20]} | {question[:32]}...", flush=True)

    out = PROJECT_ROOT / "eval" / "dataset.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[gen] 完成：{len(items)} 条 → {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
