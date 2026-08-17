"""VLM 图表多模态理解（OpenAI 兼容协议，mimo-v2.5）。

- Key 留空自动关闭（vlm_enabled=False），不影响现有 OCR 链路
- 描述图片内容用于知识检索：图表趋势/架构关系/截图要点
- 失败/无 Key 返回空串（上游降级）
"""
import base64
import io
from typing import Any

from app.core.config import get_settings

settings = get_settings()

DESCRIBE_PROMPT = """你是企业文档图表分析师。请描述这张图片的内容，用于知识检索：
- 若是图表：提取标题、坐标轴/图例含义、数据趋势、关键结论
- 若是架构图/流程图：提取节点、连接关系、整体结构
- 若是截图/示意图：提取图中文字要点与布局
输出 3~6 句简洁中文描述，不要猜测未呈现的信息。"""

_client: Any = None
_client_failed = False


def get_vlm_client():
    """OpenAI 兼容客户端懒加载；无 Key 或失败返回 None。"""
    global _client, _client_failed
    if _client or _client_failed or not settings.vlm_enabled:
        return _client
    try:
        from openai import OpenAI

        _client = OpenAI(api_key=settings.vlm_api_key, base_url=settings.vlm_base_url)
    except Exception:
        _client_failed = True
        _client = None
    return _client


def describe_image(image_bytes: bytes, page_context: str = "") -> str:
    """对图片字节生成描述文本；无 Key/失败返回空串。"""
    client = get_vlm_client()
    if client is None:
        return ""
    try:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        context_part = f"\n【所在页面上下文】{page_context[:300]}" if page_context else ""
        resp = client.chat.completions.create(
            model=settings.vlm_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": DESCRIBE_PROMPT + context_part},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=300,
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text
    except Exception as exc:
        print(f"[kra][vlm] 描述失败: {type(exc).__name__}: {str(exc)[:150]}", flush=True)
        return ""


def describe_image_or_mark(image_bytes: bytes) -> str:
    """返回描述文本；VLM 不可用或返回空时标记"[图]（无描述）"（不静默跳过）。"""
    desc = describe_image(image_bytes)
    if desc.strip():
        return desc.strip()
    return "[图]（无描述：视觉模型未提取到该图内容，图中信息不可作为回答依据）"
