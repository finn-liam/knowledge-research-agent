"""召回损失诊断：逐例分类 100 条数据集的未命中原因，定位优化杠杆。

分类口径（对每条标注 chunk）：
  top8    —— 进 fused 前 8（生产喂给 LLM 的量），命中
  fused   —— 在 fused 候选里但排到 8 之后（排序/配额问题 → rerank/top_k 可解）
  dense   —— dense 原始 top-50 可见但被阈值/RANK 滤掉（阈值问题 → 调 kb_min_score 可解）
  raw50   —— dense 原始 top-50 都没有（向量语义缺口 → 查询增强/多查询/chunk 结构可解）

用法：python eval/scripts/diagnose_recall.py
"""
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.agents.nodes import _hybrid_search  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.rag.models import encode_hybrid  # noqa: E402
from app.rag.vector_store import get_vector_store  # noqa: E402

TOP8 = 8
DIAG_K = 50


async def main() -> int:
    items = json.loads((PROJECT_ROOT / "eval" / "dataset.json").read_text(encoding="utf-8"))
    store = get_vector_store()
    await store.ensure_collection()
    settings = get_settings()
    print(f"[diag] 数据集 {len(items)} 条 | kb_min_score={settings.kb_min_score} relax={settings.kb_relax_min_score}", flush=True)

    cat = Counter()
    miss_examples: dict[str, list] = {k: [] for k in ("fused", "dense", "raw50")}
    by_type = {}  # qtype -> Counter

    for it in items:
        q = it["question"]
        rel = set()
        for r in it["relevant_chunks"]:
            did, idx = r.split("#")
            rel.add((int(did), int(idx)))

        fused = await _hybrid_search(store, q, None, top_k=20)
        fused_ids = [(h["document_id"], h["chunk_index"]) for h in fused]

        # dense 原始 top-50（不过阈值）：看语义召回上限
        res = await asyncio.to_thread(encode_hybrid, [q])
        dense_vec = res[0][0] if res and res[0] else None
        raw = await store.search_dense(dense_vec, top_k=DIAG_K) if dense_vec else []
        raw_ids = [(h["document_id"], h["chunk_index"]) for h in raw]

        qtype = it.get("type", "fact")
        by_type.setdefault(qtype, Counter())
        for r in rel:
            if r in fused_ids[:TOP8]:
                cat["top8"] += 1
                by_type[qtype]["top8"] += 1
            elif r in fused_ids:
                cat["fused"] += 1
                by_type[qtype]["fused"] += 1
                miss_examples["fused"].append((it["id"], q[:40], str(r)))
            elif r in raw_ids:
                cat["dense"] += 1
                by_type[qtype]["dense"] += 1
                miss_examples["dense"].append((it["id"], q[:40], str(r)))
            else:
                cat["raw50"] += 1
                by_type[qtype]["raw50"] += 1
                miss_examples["raw50"].append((it["id"], q[:40], str(r)))

    total = sum(cat.values())
    print(f"\n标注 chunk 总数 {total}")
    for k in ("top8", "fused", "dense", "raw50"):
        pct = cat[k] / total * 100
        print(f"  {k:<8} {cat[k]:<5} ({pct:.1f}%)")
    print("\n按题型分布（top8 / fused / dense / raw50）：")
    for qtype, c in by_type.items():
        t = sum(c.values())
        print(f"  {qtype:<10} {c['top8']}/{c['fused']}/{c['dense']}/{c['raw50']}  共{t}")

    print("\n=== raw50 未命中样例（语义缺口，最难解）===")
    for qid, q, r in miss_examples["raw50"][:12]:
        print(f"  [{qid}] {q}… ← {r}")
    print("\n=== dense 档样例（被阈值/排名滤掉）===")
    for qid, q, r in miss_examples["dense"][:8]:
        print(f"  [{qid}] {q}… ← {r}")
    print("\n=== fused 档样例（排在 top8 之外）===")
    for qid, q, r in miss_examples["fused"][:8]:
        print(f"  [{qid}] {q}… ← {r}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
