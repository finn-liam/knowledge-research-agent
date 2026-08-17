"""文档解析器：PDF（含图片 OCR）/ DOCX / MD / TXT → 纯文本。

PDF 智能解析（P1）：
  页级类型分流：文本充足=原生路径（版面还原）；文本稀少=整页 OCR（扫描件）
  版面还原：坐标排序阅读顺序、页眉页脚剔除、大字号标题转 markdown、页内图片 OCR
  每页首注入 [第N页] 标记（溯源 + LLM 引用上下文）
"""
import re
import statistics
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

SUPPORTED_EXTS = {".pdf": "pdf", ".docx": "docx", ".md": "md", ".txt": "txt"}
SUPPORTED_TYPES = set(SUPPORTED_EXTS.values())


def parse_file(path: str | Path, doc_type: str) -> str:
    path = Path(path)
    if doc_type == "pdf":
        return _parse_pdf(path)
    if doc_type == "docx":
        return _parse_docx(path)
    return _parse_text(path)


# ---------------- PDF ----------------

def _parse_pdf(path: Path) -> str:
    from app.rag.ocr import ocr_image

    if not settings.pdf_ocr_enabled:
        return _parse_pdf_text_only(path)

    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    pages: list[str] = []
    try:
        for page in doc:
            page_text = _parse_pdf_page(page, doc, ocr_image)
            if page_text.strip():
                pages.append(f"[第{page.number + 1}页]\n{page_text}")
    finally:
        doc.close()
    return _clean("\n\n".join(pages))


def _parse_pdf_text_only(path: Path) -> str:
    """回退路径：pypdf 纯文本提取（PDF_OCR_ENABLED=false 时使用）。"""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return _clean("\n\n".join(pages))


def _median_font_size(data: dict) -> float:
    sizes = [
        span["size"]
        for block in data.get("blocks", [])
        if block.get("type") == 0
        for line in block.get("lines", [])
        for span in line.get("spans", [])
    ]
    return statistics.median(sizes) if sizes else 12.0


def _parse_pdf_page(page, doc, ocr_image) -> str:
    """单页：类型分流 + 版面还原 + 图片 OCR（按坐标统一排序）。"""
    raw_text = page.get_text("text") or ""
    if len(raw_text.strip()) < settings.pdf_ocr_min_chars:
        # 扫描页：整页渲染 OCR
        pix = page.get_pixmap(dpi=150)
        return _clean(ocr_image(pix.tobytes("png")))

    data = page.get_text("dict")
    median_size = _median_font_size(data)
    page_h = page.rect.height
    top_cut = page_h * settings.pdf_margin_top
    bottom_cut = page_h * settings.pdf_margin_bottom

    items: list[tuple[float, str]] = []  # (y 坐标, 文本) 统一排序还原阅读顺序
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            bbox = line.get("bbox", (0, 0, 0, 0))
            y0, y1 = bbox[1], bbox[3]
            if y1 < top_cut or y0 > bottom_cut:
                continue  # 页眉页脚剔除
            line_text = "".join(span.get("text", "") for span in line.get("spans", []))
            if not line_text.strip():
                continue
            max_size = max(
                (span.get("size", 0) for span in line.get("spans", [])), default=0
            )
            # 标题检测：字号 ≥ 中位数 1.35 倍且行短 → markdown 标题（衔接 chunker 章节划分）
            if max_size >= median_size * 1.35 and len(line_text.strip()) <= 40:
                items.append((y0, f"# {line_text.strip()}"))
            else:
                items.append((y0, line_text))

    # 页内图片：OCR 文字 + VLM 描述（按位置排序插入）
    for img_info in page.get_images(full=True):
        try:
            xref = img_info[0]
            base = doc.extract_image(xref)
            img_bytes = base.get("image")
            if not img_bytes:
                continue
            rects = page.get_image_rects(xref)
            y_pos = rects[0].y0 if rects else page_h / 2
            parts_img: list[str] = []
            ocr_text = ocr_image(img_bytes)
            if ocr_text.strip():
                parts_img.append(f"[图] {ocr_text.strip()}")
            if settings.vlm_enabled:
                from app.rag.vlm import describe_image_or_mark

                desc = describe_image_or_mark(img_bytes)
                if desc.strip():
                    parts_img.append(f"[图描述] {desc.strip()}")
            if parts_img:
                items.append((y_pos, "\n".join(parts_img)))
        except Exception:
            continue

    items.sort(key=lambda t: (t[0] // 8, t[1]))
    return _clean("\n\n".join(text for _, text in items))


# ---------------- DOCX / TXT ----------------

def _parse_docx(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    parts = [p.text for p in document.paragraphs if p.text.strip()]
    return _clean("\n\n".join(parts))


def _parse_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return _clean(raw.decode(encoding))
        except (UnicodeDecodeError, LookupError):
            continue
    return _clean(raw.decode("utf-8", errors="ignore"))


def _clean(text: str) -> str:
    text = text.replace("\x00", "")
    # 合并多余空行、压缩连续空白
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
