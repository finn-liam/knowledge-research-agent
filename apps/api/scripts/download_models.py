"""下载向量/精排模型到项目内 models/ 目录（经 hf-mirror 镜像，不落 C 盘）。"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # knowledge-research-agent/
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

os.environ["HF_HOME"] = str(MODELS_DIR)
os.environ["HUGGINGFACE_HUB_CACHE"] = str(MODELS_DIR / "hub")
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import snapshot_download  # noqa: E402

MODELS = ["BAAI/bge-m3", "BAAI/bge-reranker-v2-m3"]

# 跳过镜像站无权访问的无关文件（imgs/.DS_Store 等），只取推理必需文件
IGNORE = ["imgs/*", "*.png", "*.jpg", "*.md", ".DS_Store", "*.gitattributes", "onnx/*", "*.onnx"]

for repo in MODELS:
    print(f"[download] {repo} -> {MODELS_DIR}", flush=True)
    path = snapshot_download(repo_id=repo, ignore_patterns=IGNORE)
    print(f"[ok] {repo} at {path}", flush=True)

print("ALL_MODELS_READY", flush=True)
