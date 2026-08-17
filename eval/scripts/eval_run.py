"""RAGAS 两阶段评估：
阶段1 检索层（进程内 _hybrid_search，全部题目，快）：context_precision / context_recall
阶段2 生成层（真实 API 全链路，抽样题目）：faithfulness / answer_relevancy
输出：eval/report.md + eval/results/baseline.json（首次存档为基线）

用法：python eval/scripts/eval_run.py [--gen N] [--save-baseline]
"""
import argparse
import asyncio
import json
import random
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # knowledge-research-agent
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

import httpx
from sqlalchemy import select  # noqa: E402

from app.agents.nodes import _hybrid_search  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.research import DocumentChunk  # noqa: E402
from app.rag.vector_store import get_vector_store  # noqa: E402

BASE = "http://127.0.0.1:8000"
EVAL_DIR = Path(__file__).resolve().parents[1]  # eval/


def load_dataset() -> list[dict]:
    path = EVAL_DIR / "dataset.json"
    if not path.exists():
        print("[eval] 缺少 dataset.json，请先运行 eval_dataset_gen.py", flush=True)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


async def chunk_text_map() -> dict[str, str]:
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(DocumentChunk.document_id, DocumentChunk.chunk_index, DocumentChunk.text)
            )
        ).all()
    return {f"{r[0]}#{r[1]}": r[2] for r in rows}


async def run_retrieval_layer(items: list[dict], text_map: dict[str, str]) -> list[dict]:
    """阶段1：进程内混合检索，产出 ragas 需要的 retrieved_contexts 与 reference。"""
    store = get_vector_store()
    await store.ensure_collection()
    samples = []
    for it in items:
        fused = await _hybrid_search(store, it["question"], None)
        contexts = [f"{h['document_name']} · 片段{h['chunk_index']+1}\n{(h.get('text') or '')[:300]}" for h in fused[:8]]
        reference = [text_map[k][:600] for k in it["relevant_chunks"] if k in text_map]
        samples.append({
            "user_input": it["question"],
            "reference": reference,
            "retrieved_contexts": contexts,
            "doc_name": it.get("doc_name", ""),
        })
    return samples


async def run_generation_layer(items: list[dict], text_map: dict[str, str], limit: int) -> list[dict]:
    """阶段2：真实 API 全链路（含增强/grader/多源/verifier），拿最终报告作 response。"""
    async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as client:
        samples = []
        for it in items[:limit]:
            r = await client.post("/api/v1/research", json={"query": it["question"]})
            r.raise_for_status()
            tid = r.json()["task_id"]
            async with client.stream("GET", f"/api/v1/research/{tid}/stream", timeout=420.0) as stream:
                ev = None
                async for line in stream.aiter_lines():
                    if line.startswith("event: "):
                        ev = line[7:]
                    elif line.startswith("data: ") and ev:
                        if ev == "stream_end":
                            break
                        ev = None
            detail = (await client.get(f"/api/v1/research/{tid}")).json()
            report = (detail.get("report") or {}).get("markdown", "")
            sources = detail.get("sources", [])
            samples.append({
                "user_input": it["question"],
                "response": report,
                "retrieved_contexts": [s.get("snippet", "") for s in sources],
                "context_types": [s.get("type", "") for s in sources],
                "reference": [text_map[k][:600] for k in it["relevant_chunks"] if k in text_map],
                "doc_name": it.get("doc_name", ""),
                "qtype": it.get("type", "fact"),
            })
            print(f"  [gen-layer] {it['id']} 完成 | 报告 {len(report)} 字", flush=True)
    return samples


def build_ragas_samples(samples: list[dict]) -> list:
    from ragas import SingleTurnSample

    out = []
    for s in samples:
        kwargs = {"user_input": s["user_input"]}
        if s.get("response"):
            kwargs["response"] = s["response"]
        kwargs["retrieved_contexts"] = s["retrieved_contexts"]
        # ragas 0.4.x: reference 为单个字符串
        ref = s.get("reference") or []
        kwargs["reference"] = "\n".join(ref) if isinstance(ref, list) else str(ref)
        out.append(SingleTurnSample(**kwargs))
    return out


def _is_enterprise_ctx(sample: dict, idx: int) -> bool:
    """按来源类型判断上下文是否为企业知识库（context_types 与 contexts 对齐）。"""
    types = sample.get("context_types") or []
    if idx < len(types):
        return types[idx] == "enterprise"
    return False


def _mean(v):
    """ragas 结果兼容：dict[str, list] / DataFrame / 标量；过滤 NaN。"""
    import math

    if v is None:
        return 0.0
    if isinstance(v, (list, tuple)):
        vals = [float(x) for x in v if not (isinstance(x, float) and math.isnan(x))]
        return sum(vals) / len(vals) if vals else 0.0
    try:
        return float(v.mean())  # pandas Series / numpy
    except Exception:
        return 0.0 if math.isnan(float(v)) else float(v)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gen", type=int, default=8, help="生成层抽样条数")
    parser.add_argument("--save-baseline", action="store_true", help="首次运行存档基线")
    args = parser.parse_args()

    items = load_dataset()
    text_map = await chunk_text_map()
    settings = get_settings()
    print(f"[eval] 数据集 {len(items)} 条 | 生成层抽样 {min(args.gen, len(items))} 条", flush=True)

    # ---- LLM 适配器（DeepSeek → ragas）----
    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper

    chat = ChatOpenAI(
        model=settings.deepseek_model, api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url, temperature=0.1,
    )
    ragas_llm = LangchainLLMWrapper(chat)

    # ---- 阶段1：检索层 ----
    t0 = time.time()
    retr_samples = await run_retrieval_layer(items, text_map)
    print(f"[eval] 阶段1 检索层完成（{time.time()-t0:.0f}s）", flush=True)

    # ---- 阶段2：生成层（真实 API）----
    t0 = time.time()
    gen_samples = await run_generation_layer(items, text_map, args.gen)
    print(f"[eval] 阶段2 生成层完成（{time.time()-t0:.0f}s）", flush=True)

    # ---- ragas 评分 ----
    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.metrics import context_precision, context_recall, faithfulness

    # ragas 0.4.x：指标为实例，直接赋值 llm；evaluate 级也传（双保险）
    # 注：answer_relevancy 已暂缓——其 question_generation 依赖 n>1 与 embedding 相似度，
    # 与 DeepSeek（仅支持 n=1）兼容性存在问题（strictness=1 修复未完全生效）。
    for m in (faithfulness, context_precision, context_recall):
        m.llm = ragas_llm

    # 本地 bge-m3 embeddings（避免 HF 联网探测）
    from langchain_core.embeddings import Embeddings

    class LocalBgeM3(Embeddings):
        def embed_documents(self, texts):
            from app.rag.models import get_embedder

            model = get_embedder()
            return model.encode(texts, normalize_embeddings=True).tolist()

        def embed_query(self, text):
            from app.rag.models import get_embedder

            model = get_embedder()
            return model.encode([text], normalize_embeddings=True).tolist()[0]

    emb_wrapper = LangchainEmbeddingsWrapper(LocalBgeM3())

    # 评分超时/重试控制（DeepSeek 推理模型较慢；放宽避免 nan）
    from ragas.run_config import RunConfig

    run_cfg = RunConfig(timeout=400, max_retries=2)

    retr_ds = EvaluationDataset(samples=build_ragas_samples(retr_samples))
    gen_ds = EvaluationDataset(samples=build_ragas_samples(gen_samples))

    r_retr = evaluate(
        retr_ds, metrics=[context_precision, context_recall],
        llm=ragas_llm, embeddings=emb_wrapper, run_config=run_cfg,
    )
    r_gen = evaluate(
        gen_ds,
        metrics=[faithfulness, context_precision, context_recall],
        llm=ragas_llm, embeddings=emb_wrapper, run_config=run_cfg,
    )
    # 按题型分项评分（chart 题独立口径：诚实"未显示"声明不被误扣）
    r_gen_chart = None
    r_gen_text = None
    chart_samples = [s for s in gen_samples if s.get("qtype") == "chart"]
    text_samples = [s for s in gen_samples if s.get("qtype") != "chart"]
    if chart_samples:
        r_gen_chart = evaluate(
            EvaluationDataset(samples=build_ragas_samples(chart_samples)),
            metrics=[faithfulness], llm=ragas_llm, embeddings=emb_wrapper,
            run_config=run_cfg,
        )
    if text_samples:
        r_gen_text = evaluate(
            EvaluationDataset(samples=build_ragas_samples(text_samples)),
            metrics=[faithfulness], llm=ragas_llm, embeddings=emb_wrapper,
            run_config=run_cfg,
        )
    # ---- P2 双口径：生成层 KB 口径（仅 enterprise 来源，对比 KB reference）----
    gen_kb_samples = []
    for it in gen_samples:
        kb_contexts = [c for i, c in enumerate(it["retrieved_contexts"]) if _is_enterprise_ctx(it, i)]
        if kb_contexts:
            s = dict(it)
            s["retrieved_contexts"] = kb_contexts
            gen_kb_samples.append(s)
    r_gen_kb = None
    if gen_kb_samples:
        gen_kb_ds = EvaluationDataset(samples=build_ragas_samples(gen_kb_samples))
        r_gen_kb = evaluate(
            gen_kb_ds,
            metrics=[context_precision, context_recall],
            llm=ragas_llm, embeddings=emb_wrapper, run_config=run_cfg,
        )

    # ---- 汇总（防御性兼容 list/Series/标量）----
    results = {
        "retrieval_layer": {
            "context_precision": _mean(r_retr["context_precision"]),
            "context_recall": _mean(r_retr["context_recall"]),
        },
        "generation_layer": {
            "faithfulness": _mean(r_gen["faithfulness"]),
            "context_precision": _mean(r_gen["context_precision"]),
            "context_recall": _mean(r_gen["context_recall"]),
        },
        "faithfulness_by_type": {
            "chart": _mean(r_gen_chart["faithfulness"]) if r_gen_chart is not None else None,
            "text": _mean(r_gen_text["faithfulness"]) if r_gen_text is not None else None,
        },
        "generation_layer_kb": (
            {
                "context_precision": _mean(r_gen_kb["context_precision"]),
                "context_recall": _mean(r_gen_kb["context_recall"]),
            }
            if r_gen_kb is not None
            else {}
        ),
        "meta": {"dataset_size": len(items), "gen_sample": args.gen, "ts": time.strftime("%Y-%m-%d %H:%M")},
    }

    # ---- report.md ----
    import math as _math

    def _valid_count(v):
        if isinstance(v, (list, tuple)):
            return sum(1 for x in v if not (isinstance(x, float) and _math.isnan(x)))
        return 1 if v is not None else 0

    lines = ["# RAG 评估报告", ""]
    lines.append(f"> 数据集 {len(items)} 条 | 生成层抽样 {args.gen} 条 | 时间 {results['meta']['ts']}")
    lines.append("")
    lines.append("## 指标汇总")
    lines.append("")
    lines.append("| 层 | 指标 | 分数 | 有效样本 |")
    lines.append("|---|---|---|---|")
    for k, v in results["retrieval_layer"].items():
        lines.append(f"| 检索层 | {k} | {v:.3f} | {_valid_count(r_retr[k])}/{len(items)} |")
    for k, v in results["generation_layer"].items():
        lines.append(f"| 生成层 | {k} | {v:.3f} | {_valid_count(r_gen[k])}/{args.gen} |")
    if results.get("generation_layer_kb"):
        for k, v in results["generation_layer_kb"].items():
            lines.append(f"| 生成层·KB口径 | {k} | {v:.3f} | - |")
    for qt, v in results.get("faithfulness_by_type", {}).items():
        if v is not None:
            lines.append(f"| 生成层·{qt}题 | faithfulness | {v:.3f} | - |")
    lines.append("")

    # baseline 对比
    baseline_path = EVAL_DIR / "results" / "baseline.json"
    if baseline_path.exists():
        base = json.loads(baseline_path.read_text(encoding="utf-8"))
        lines.append("## 与基线对比")
        lines.append("")
        lines.append("| 指标 | 基线 | 本次 | 变化 |")
        lines.append("|---|---|---|---|")
        for section in ("retrieval_layer", "generation_layer"):
            for k, v in results[section].items():
                b = base.get(section, {}).get(k)
                if b is not None:
                    delta = v - b
                    mark = "✅" if delta >= 0.005 else ("⚠️" if delta <= -0.005 else "—")
                    lines.append(f"| {k} | {b:.3f} | {v:.3f} | {delta:+.3f} {mark} |")
        lines.append("")
    else:
        lines.append("> 首次运行：本结果将存档为基线。")
        lines.append("")

    # per-question 明细（低分 <0.6 高亮；防御性取值）
    lines.append("## 生成层明细（faithfulness 低分 <0.6 高亮）")
    lines.append("")

    def _col(r, name):
        try:
            v = r[name]
            return list(v) if isinstance(v, (list, tuple)) else [v]
        except Exception:
            return []

    fa_list = _col(r_gen, "faithfulness")
    for i, it in enumerate(gen_samples[: len(fa_list)]):
        fa = fa_list[i] if i < len(fa_list) else None
        q = str(it.get("user_input", ""))[:50]
        fa_s = "-" if fa is None else f"{float(fa):.3f}"
        flag = " ⚠️" if (fa is not None and float(fa) < 0.6) else ""
        lines.append(f"- {q} | faithfulness={fa_s}{flag}")
    lines.append("")

    report_path = EVAL_DIR / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[eval] 报告已写入 {report_path}", flush=True)

    if args.save_baseline or not baseline_path.exists():
        baseline_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[eval] 基线已存档 {baseline_path}", flush=True)

    print(f"[eval] 检索层 precision={results['retrieval_layer']['context_precision']:.3f} recall={results['retrieval_layer']['context_recall']:.3f}", flush=True)
    print(f"[eval] 生成层 faithfulness={results['generation_layer']['faithfulness']:.3f}", flush=True)
    print("EVAL_DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
