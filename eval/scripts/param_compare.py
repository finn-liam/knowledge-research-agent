"""P1 参数对比：在 40 条数据集上对比"优化前/优化后"检索参数对 precision/recall 的影响。

用法：python eval/scripts/param_compare.py
（进程内检索，不调 LLM，约 2~4 分钟）
"""
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.agents.nodes import _fuse_hybrid, _hybrid_search  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.rag.models import encode_hybrid  # noqa: E402
from app.rag.vector_store import get_vector_store  # noqa: E402

BEFORE = {"top_k": 20, "min_score": 0.45, "relax": 0.35}
AFTER = {"top_k": 30, "min_score": 0.40, "relax": 0.30}


async def run_one(store, q: str, cfg: dict, settings) -> list[tuple]:
    settings.kb_min_score = cfg["min_score"]
    settings.kb_relax_min_score = cfg["relax"]
    fused = await _hybrid_search(store, q, None, top_k=cfg["top_k"])
    return [(h["document_id"], h["chunk_index"]) for h in fused]


def evaluate_recall(hits, relevant: list[str]) -> tuple[float, float]:
    """返回 (precision, recall)：命中 = (document_id, chunk_index) 匹配 relevant。"""
    hit_set = set(hits)
    rel_set = set()
    for r in relevant:
        did, idx = r.split("#")
        rel_set.add((int(did), int(idx)))
    if not rel_set:
        return 0.0, 0.0
    overlap = len(hit_set & rel_set)
    precision = overlap / len(hit_set) if hit_set else 0.0
    recall = overlap / len(rel_set)
    return precision, recall


async def main() -> int:
    items = json.loads((PROJECT_ROOT / "eval" / "dataset.json").read_text(encoding="utf-8"))
    store = get_vector_store()
    await store.ensure_collection()
    settings = get_settings()

    agg = {"before": {"p": [], "r": []}, "after": {"p": [], "r": []}}
    for it in items:
        for name, cfg in (("before", BEFORE), ("after", AFTER)):
            hits = await run_one(store, it["question"], cfg, settings)
            p, r = evaluate_recall(hits, it["relevant_chunks"])
            agg[name]["p"].append(p)
            agg[name]["r"].append(r)

    def mean(x):
        return sum(x) / len(x) if x else 0.0

    print(f"数据集 {len(items)} 条", flush=True)
    print(f"{'配置':<10} {'precision':<10} {'recall':<10}", flush=True)
    print(f"{'优化前':<10} {mean(agg['before']['p']):<10.3f} {mean(agg['before']['r']):<10.3f}", flush=True)
    print(f"{'优化后':<10} {mean(agg['after']['p']):<10.3f} {mean(agg['after']['r']):<10.3f}", flush=True)
    delta_r = mean(agg["after"]["r"]) - mean(agg["before"]["r"])
    delta_p = mean(agg["after"]["p"]) - mean(agg["before"]["p"])
    print(f"recall 变化: {delta_r:+.3f} | precision 变化: {delta_p:+.3f}", flush=True)
    keep = delta_r >= 0.005 and delta_p >= -0.03
    print("PARAM_RECOMMEND_KEEP" if keep else "PARAM_RECOMMEND_REVERT", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
