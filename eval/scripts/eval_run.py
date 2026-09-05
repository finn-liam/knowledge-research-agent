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

from app.agents.mock_data import mock_query_process  # noqa: E402
from app.agents.nodes import (  # noqa: E402
    _apply_rerank,
    _expand_with_siblings,
    _hybrid_search,
    _multi_query_search,
)
from app.agents.prompts import QUERY_PROCESS_PROMPT  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.llm.gateway import get_llm  # noqa: E402
from app.models.research import DocumentChunk  # noqa: E402
from app.rag.vector_store import get_vector_store  # noqa: E402

BASE = "http://127.0.0.1:8000"
EVAL_DIR = Path(__file__).resolve().parents[1]  # eval/

# 生产 KB 路径的配额（与 nodes.py 对齐：merger 输出 MAX_GRADE_SOURCES=12 给 grader）
EVAL_TOP_K = 20
EVAL_CONTEXT_K = 12
ENH_CACHE_PATH = EVAL_DIR / "results" / "enh_cache.json"


async def _enhance_cached(llm, question: str) -> dict:
    """查询增强结果缓存：与 ab_recall.py 共用（首轮 LLM 逐条生成，后续秒级）。

    条目缺 hyde 字段（旧版缓存）时回填——HyDE 变体依赖该字段。
    """
    import json as _json

    cache = (
        _json.loads(ENH_CACHE_PATH.read_text(encoding="utf-8"))
        if ENH_CACHE_PATH.exists()
        else {}
    )
    if question in cache and "hyde" in cache[question]:
        return cache[question]
    processed = await llm.extract_json(
        QUERY_PROCESS_PROMPT.format(query=question), mock_query_process(question)
    )
    cache[question] = {
        "rewritten_query": processed.get("rewritten_query") or question,
        "keywords": processed.get("keywords") or [],
        "sub_queries": processed.get("sub_queries") or [],
        "hyde": str(processed.get("hyde") or ""),
    }
    ENH_CACHE_PATH.write_text(_json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return cache[question]


async def production_kb_candidates(store, question: str, llm) -> list[dict]:
    """对齐生产 kb_retriever_node 的 KB 检索路径：原话主查询+子查询+HyDE → 兄弟扩展 → 精排。

    llm 传 None 时退化为原问题单路检索（仍做兄弟扩展与精排）。
    """
    settings = get_settings()
    sub_qs, hyde_text = [], ""
    if llm is not None and settings.query_processing:
        processed = await _enhance_cached(llm, question)
        sub_qs = [
            s.strip() for s in (processed.get("sub_queries") or [])
            if isinstance(s, str) and s.strip() and s.strip() != question
        ][:2]
        if settings.hyde_enabled and settings.multi_query:
            hyde_text = str(processed.get("hyde") or "").strip()

    # 主查询用原话（与生产 kb_retriever_node 一致，见 ab_recall orig_multi 结论）
    pairs = [(question, None)]
    pairs += [(s, None) for s in sub_qs]
    if hyde_text and hyde_text != question:
        pairs.append((hyde_text, None))
    fused = await _multi_query_search(store, pairs, top_k=EVAL_TOP_K)
    if not fused and (sub_qs or hyde_text):
        fused = await _hybrid_search(store, question, None)
    if settings.sibling_expand and fused:
        fused = await _expand_with_siblings(fused)

    # 不做单文档配额（A/B 实测有害）；精排后由生产 merger 的 top-12 窗口截取
    if settings.rerank_enabled:
        fused = _apply_rerank(question, fused)
    return fused


def load_dataset() -> list[dict]:
    path = EVAL_DIR / "dataset.json"
    if not path.exists():
        print("[eval] 缺少 dataset.json，请先运行 eval_dataset_gen.py", flush=True)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


async def chunk_text_map() -> tuple[dict[str, str], dict[str, str]]:
    """返回 (child_map, parent_map)：key = document_id#chunk_index。

    child  = 切片检索单元文本（严格口径）
    parent = 章节级上下文（对齐生产生成时喂给 LLM 的上下文口径）
    """
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(
                    DocumentChunk.document_id, DocumentChunk.chunk_index,
                    DocumentChunk.text, DocumentChunk.parent_text,
                )
            )
        ).all()
    child = {f"{r[0]}#{r[1]}": r[2] for r in rows}
    parent = {f"{r[0]}#{r[1]}": (r[3] or r[2]) for r in rows}
    return child, parent


async def run_retrieval_layer(
    items: list[dict], child_map: dict[str, str], parent_map: dict[str, str]
) -> list[dict]:
    """阶段1：进程内混合检索，产出 ragas 需要的 retrieved_contexts 与 reference。

    双口径（P0 评估口径修复）：
      retrieved_contexts          —— child 口径（严格：检索单元前 300 字，历史口径）
      retrieved_contexts_parent   —— parent 口径（对齐生产：章节级上下文）
    检索只跑一遍，两套上下文共享同一批命中。

    P2 起上下文取自「生产对齐路径」（增强+多查询+配额+精排），
    同时保留 raw（原问题单路 RRF）的 ID 级指标做对照（无 LLM 成本）。
    """
    store = get_vector_store()
    await store.ensure_collection()
    settings = get_settings()
    llm = get_llm() if settings.query_processing else None
    samples = []
    for it in items:
        q = it["question"]
        fused = await production_kb_candidates(store, q, llm)
        fused_raw = await _hybrid_search(store, q, None, top_k=EVAL_TOP_K)

        child_contexts = [
            f"{h['document_name']} · 片段{h['chunk_index']+1}\n{(h.get('text') or '')[:300]}"
            for h in fused[:EVAL_CONTEXT_K]
        ]
        parent_contexts = []
        for h in fused[:EVAL_CONTEXT_K]:
            key = f"{h['document_id']}#{h['chunk_index']}"
            p = parent_map.get(key) or ""
            parent_contexts.append(
                f"{h['document_name']} · 片段{h['chunk_index']+1}（章节上下文）\n{p[:1600]}"
            )
        reference = [child_map[k][:600] for k in it["relevant_chunks"] if k in child_map]

        # ID 级对照（免 LLM）：命中 = (document_id, chunk_index) 匹配标注
        def id_hits(hits):
            return {(h["document_id"], h["chunk_index"]) for h in hits[:EVAL_CONTEXT_K]}

        rel_ids = set()
        for k in it["relevant_chunks"]:
            if "#" in k:
                d, i = k.split("#")
                rel_ids.add((int(d), int(i)))
        prod_ids, raw_ids = id_hits(fused), id_hits(fused_raw)
        overlap_p, overlap_r = len(prod_ids & rel_ids), len(raw_ids & rel_ids)

        samples.append({
            "user_input": q,
            "reference": reference,
            "retrieved_contexts": child_contexts,
            "retrieved_contexts_parent": parent_contexts,
            "doc_name": it.get("doc_name", ""),
            "id_precision_prod": overlap_p / len(prod_ids) if prod_ids else 0.0,
            "id_recall_prod": overlap_p / len(rel_ids) if rel_ids else 0.0,
            "id_precision_raw": overlap_r / len(raw_ids) if raw_ids else 0.0,
            "id_recall_raw": overlap_r / len(rel_ids) if rel_ids else 0.0,
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


def build_ragas_samples(samples: list[dict], ctx_key: str = "retrieved_contexts") -> list:
    from ragas import SingleTurnSample

    out = []
    for s in samples:
        kwargs = {"user_input": s["user_input"]}
        if s.get("response"):
            kwargs["response"] = s["response"]
        kwargs["retrieved_contexts"] = s[ctx_key]
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


def _ci95(v) -> float | None:
    """95% 置信区间半宽（±）：基于每样本分数；样本 <2 或无波动返回 None。"""
    import math

    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        vals = [float(x) for x in v if not (isinstance(x, float) and math.isnan(x))]
    else:
        try:
            vals = [float(x) for x in list(v) if not (isinstance(x, float) and math.isnan(x))]
        except Exception:
            return None
    n = len(vals)
    if n < 2:
        return None
    mean = sum(vals) / n
    var = sum((x - mean) ** 2 for x in vals) / (n - 1)
    sd = math.sqrt(var)
    if sd == 0:
        return None
    return 1.96 * sd / math.sqrt(n)


def _fmt_score(v: float, raw) -> str:
    """分数 + 95% 置信区间（样本充足时）。"""
    ci = _ci95(raw)
    return f"{v:.3f} ± {ci:.3f}" if ci is not None else f"{v:.3f}"


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gen", type=int, default=8, help="生成层抽样条数（0=仅跑检索层）")
    parser.add_argument("--limit", type=int, default=0, help="只取数据集前 N 条试跑（0=全量；用于低成本验证）")
    parser.add_argument("--save-baseline", action="store_true", help="首次运行存档基线")
    args = parser.parse_args()

    items = load_dataset()
    if args.limit > 0:
        items = items[: args.limit]
    child_map, parent_map = await chunk_text_map()
    settings = get_settings()
    print(f"[eval] 数据集 {len(items)} 条 | 生成层抽样 {min(args.gen, len(items))} 条", flush=True)

    # ---- LLM 适配器（ragas 裁判，与被测系统解耦）----
    # 默认用 DeepSeek 主配置；设置 EVAL_JUDGE_MODEL/BASE_URL/API_KEY 可指向
    # 任意 OpenAI 兼容端点（如 Ollama: http://localhost:11434/v1 + qwen2.5:7b，Key 随意填）。
    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper

    judge_model = settings.eval_judge_model or settings.deepseek_model
    judge_base = settings.eval_judge_base_url or settings.deepseek_base_url
    judge_key = settings.eval_judge_api_key or settings.deepseek_api_key
    print(f"[eval] ragas 裁判模型: {judge_model} @ {judge_base}", flush=True)
    chat = ChatOpenAI(
        model=judge_model, api_key=judge_key,
        base_url=judge_base, temperature=0.1,
    )
    ragas_llm = LangchainLLMWrapper(chat)

    # ---- 阶段1：检索层（进程内，双口径上下文） ----
    t0 = time.time()
    retr_samples = await run_retrieval_layer(items, child_map, parent_map)
    print(f"[eval] 阶段1 检索层完成（{time.time()-t0:.0f}s）", flush=True)

    # ---- 阶段2：生成层（真实 API）----
    t0 = time.time()
    gen_samples = await run_generation_layer(items, child_map, args.gen)
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
    # P0 双口径：parent 口径对齐生产生成时的章节级上下文
    retr_ds_parent = EvaluationDataset(
        samples=build_ragas_samples(retr_samples, ctx_key="retrieved_contexts_parent")
    )

    r_retr = evaluate(
        retr_ds, metrics=[context_precision, context_recall],
        llm=ragas_llm, embeddings=emb_wrapper, run_config=run_cfg,
    )
    r_retr_parent = evaluate(
        retr_ds_parent, metrics=[context_precision, context_recall],
        llm=ragas_llm, embeddings=emb_wrapper, run_config=run_cfg,
    )
    r_gen = None
    if gen_samples:
        gen_ds = EvaluationDataset(samples=build_ragas_samples(gen_samples))
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
    # ID 级对照：生产对齐路径 vs 原始单路检索（免 LLM，确定性指标）
    def _id_mean(key: str) -> float:
        return sum(s[key] for s in retr_samples) / len(retr_samples) if retr_samples else 0.0

    results = {
        "retrieval_layer": {
            "context_precision": _mean(r_retr["context_precision"]),
            "context_recall": _mean(r_retr["context_recall"]),
        },
        "retrieval_layer_parent": {
            "context_precision": _mean(r_retr_parent["context_precision"]),
            "context_recall": _mean(r_retr_parent["context_recall"]),
        },
        "retrieval_id_level": {
            "precision_production": _id_mean("id_precision_prod"),
            "recall_production": _id_mean("id_recall_prod"),
            "precision_raw": _id_mean("id_precision_raw"),
            "recall_raw": _id_mean("id_recall_raw"),
        },
        "generation_layer": (
            {
                "faithfulness": _mean(r_gen["faithfulness"]),
                "context_precision": _mean(r_gen["context_precision"]),
                "context_recall": _mean(r_gen["context_recall"]),
            }
            if r_gen is not None
            else {}
        ),
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
        try:
            return sum(1 for x in list(v) if not (isinstance(x, float) and _math.isnan(x)))
        except Exception:
            return 1 if v is not None else 0

    lines = ["# RAG 评估报告", ""]
    lines.append(
        f"> 数据集 {len(items)} 条 | 生成层抽样 {args.gen} 条 | 时间 {results['meta']['ts']} | "
        "检索层已对齐生产路径（增强+多查询+精排，窗口=MAX_GRADE_SOURCES）"
    )
    lines.append("")
    lines.append("## 指标汇总")
    lines.append("")
    lines.append("| 层 | 指标 | 分数(±95%CI) | 有效样本 |")
    lines.append("|---|---|---|---|")
    for k, v in results["retrieval_layer"].items():
        lines.append(f"| 检索层(child口径) | {k} | {_fmt_score(v, r_retr[k])} | {_valid_count(r_retr[k])}/{len(items)} |")
    for k, v in results["retrieval_layer_parent"].items():
        lines.append(f"| 检索层(parent口径) | {k} | {_fmt_score(v, r_retr_parent[k])} | {_valid_count(r_retr_parent[k])}/{len(items)} |")
    idl = results.get("retrieval_id_level", {})
    if idl:
        lines.append(
            f"| 检索层·ID级 | precision(生产/原始) | {idl['precision_production']:.3f} / {idl['precision_raw']:.3f} | {len(items)}/{len(items)} |"
        )
        lines.append(
            f"| 检索层·ID级 | recall(生产/原始) | {idl['recall_production']:.3f} / {idl['recall_raw']:.3f} | {len(items)}/{len(items)} |"
        )
    for k, v in results["generation_layer"].items():
        lines.append(f"| 生成层 | {k} | {_fmt_score(v, r_gen[k])} | {_valid_count(r_gen[k])}/{args.gen} |")
    if results.get("generation_layer_kb"):
        for k, v in results["generation_layer_kb"].items():
            lines.append(f"| 生成层·KB口径 | {k} | {_fmt_score(v, r_gen_kb[k])} | - |")
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

    # per-question 明细（低分 <0.6 高亮；防御性取值；仅生成层运行时输出）
    if r_gen is not None:
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

    print(f"[eval] 检索层(child口径)  precision={results['retrieval_layer']['context_precision']:.3f} recall={results['retrieval_layer']['context_recall']:.3f}", flush=True)
    print(f"[eval] 检索层(parent口径) precision={results['retrieval_layer_parent']['context_precision']:.3f} recall={results['retrieval_layer_parent']['context_recall']:.3f}", flush=True)
    idl = results.get("retrieval_id_level", {})
    if idl:
        print(
            f"[eval] ID级(top{EVAL_CONTEXT_K}) 生产 precision={idl['precision_production']:.3f} recall={idl['recall_production']:.3f}"
            f" | 原始 precision={idl['precision_raw']:.3f} recall={idl['recall_raw']:.3f}",
            flush=True,
        )
    if r_gen is not None:
        print(f"[eval] 生成层 faithfulness={results['generation_layer']['faithfulness']:.3f}", flush=True)
    print("EVAL_DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
