"""bge-m3 向量模型 / bge-reranker-v2-m3 精排模型：懒加载，模型文件在项目 models/ 目录。

未下载完成或加载失败时优雅降级（返回 None），不阻塞演示链路。
"""
import os
from typing import Any

from app.core.config import get_settings

settings = get_settings()

# 必须在导入 sentence_transformers 之前设置缓存目录（项目内 models/，不落 C 盘）
os.environ.setdefault("HF_HOME", str(settings.models_dir))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(settings.models_dir / "hub"))
os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)

_embedder: Any = None
_embedder_failed = False
_reranker: Any = None
_reranker_failed = False
_bge3: Any = None
_bge3_failed = False


def get_embedder():
    global _embedder, _embedder_failed
    if _embedder or _embedder_failed:
        return _embedder
    try:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(settings.embedding_model, device="cpu")
    except Exception:
        _embedder_failed = True
        _embedder = None
    return _embedder


def get_bge3():
    """BGEM3FlagModel（bge-m3 官方）：一次前向产出 dense + sparse 词法权重。

    混合检索（方案 A）的主编码器；加载失败降级为 None（上层回退纯 dense）。
    """
    global _bge3, _bge3_failed
    if _bge3 or _bge3_failed:
        return _bge3
    try:
        from FlagEmbedding import BGEM3FlagModel

        hub = settings.models_dir / "hub" / "models--BAAI--bge-m3" / "snapshots"
        snaps = [p for p in hub.iterdir()] if hub.is_dir() else []
        model_path = str(snaps[0]) if snaps else settings.embedding_model
        _bge3 = BGEM3FlagModel(model_path, device="cpu", use_fp16=False)
    except Exception:
        _bge3_failed = True
        _bge3 = None
    return _bge3


def encode_hybrid(texts: list[str]) -> tuple[list[list[float]] | None, list[dict] | None]:
    """返回 (dense_vecs, sparse_vecs)；sparse_vecs=[{indices:[int], values:[float]}]。

    模型不可用时返回 (None, None)，上层降级纯 dense 或跳过。
    """
    model = get_bge3()
    if model is None:
        return None, None
    out = model.encode(texts, return_dense=True, return_sparse=True, max_length=512)
    dense = [v.tolist() for v in out["dense_vecs"]]
    sparse = [
        {
            "indices": [int(k) for k in lw.keys()],
            "values": [float(v) for v in lw.values()],
        }
        for lw in out["lexical_weights"]
    ]
    return dense, sparse


def get_reranker():
    global _reranker, _reranker_failed
    if _reranker or _reranker_failed:
        return _reranker
    try:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(settings.reranker_model, device="cpu")
    except Exception:
        _reranker_failed = True
        _reranker = None
    return _reranker


def rerank_scores(query: str, snippets: list[str]) -> list[float] | None:
    """返回 0~1 相关度；模型不可用时返回 None（上层用启发式分数降级）。"""
    model = get_reranker()
    if model is None or not snippets:
        return None
    try:
        import math

        pairs = [[query, s[:512]] for s in snippets]
        logits = model.predict(pairs)
        return [1.0 / (1.0 + math.exp(-float(x))) for x in logits]
    except Exception:
        return None
