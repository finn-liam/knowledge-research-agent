"""RapidOCR 自测：中文图片 OCR + 模型落项目目录验证。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # knowledge-research-agent
os.environ["RAPIDOCR_MODEL_DIR"] = str(PROJECT_ROOT / "models" / "rapidocr")

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
img = Image.new("RGB", (500, 120), "white")
d = ImageDraw.Draw(img)
# 中文字体按平台自适应（Windows 用 msyh.ttc；Linux 用 Noto CJK；找不到回退默认字体）
_font_path = r"C:\Windows\Fonts\msyh.ttc"
if not os.path.exists(_font_path):
    _font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font = None
try:
    font = ImageFont.truetype(_font_path, 32)
except OSError:
    font = ImageFont.load_default()
d.text((20, 30), "企业知识管理平台", fill="black", font=font)
d.text((20, 75), "RAG 检索增强生成", fill="black", font=font)
png_path = TESTDATA / "ocr_test.png"
img.save(str(png_path))

from rapidocr_onnxruntime import RapidOCR  # noqa: E402

engine = RapidOCR()
result, _ = engine(str(png_path))
texts = [r[1] for r in result] if result else []
print("OCR 结果:", " | ".join(texts), flush=True)
print("OCR_OK" if texts else "OCR_FAIL", flush=True)
