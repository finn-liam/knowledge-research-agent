"""RapidOCR 封装：懒加载、失败降级、中文识别。

模型随 rapidocr-onnxruntime 包自带（conda 环境 F 盘，不落 C 盘）。
加载失败返回 None（上层降级为纯文本提取，链路不中断）。
"""
from typing import Any

_engine: Any = None
_engine_failed = False


def get_ocr():
    global _engine, _engine_failed
    if _engine or _engine_failed:
        return _engine
    try:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    except Exception:
        _engine_failed = True
        _engine = None
    return _engine


def ocr_image(image_bytes: bytes) -> str:
    """对图片字节做 OCR，返回识别文本（多行用换行连接）；失败返回空串。"""
    engine = get_ocr()
    if engine is None:
        return ""
    try:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        result, _ = engine(img)
        if not result:
            return ""
        lines = [str(r[1]) for r in result if len(r) > 1 and r[1]]
        return "\n".join(lines)
    except Exception:
        return ""
