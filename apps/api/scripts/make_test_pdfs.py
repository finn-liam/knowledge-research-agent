"""构造 PDF 智能解析测试件：T1 图文混排 + T2 纯扫描。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz  # noqa: E402

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
PNG = TESTDATA / "ocr_test.png"
assert PNG.exists(), "缺少 ocr_test.png，先跑 ocr_test.py"

# ---- T1：图文混排 PDF（文本 + 带字截图）----
doc = fitz.open()
page = doc.new_page()
page.insert_text((72, 72), "年度技术总结", fontsize=20)
page.insert_text((72, 120), "本年度完成了知识管理平台的搭建，覆盖检索与生成全链路。", fontsize=12)
page.insert_text((72, 150), "平台整体采用 Agentic RAG 架构，检索部分使用混合检索方案。", fontsize=12)
page.insert_image(fitz.Rect(72, 180, 420, 260), filename=str(PNG))
page.insert_text((72, 290), "如上图所示，平台覆盖企业知识管理与检索增强生成两大能力。", fontsize=12)
doc.save(str(TESTDATA / "test_mixed.pdf"))
doc.close()
print("[t1] 图文混排 PDF 已生成", flush=True)

# ---- T2：纯扫描 PDF（整页只有图片）----
doc = fitz.open()
page = doc.new_page()
page.insert_image(fitz.Rect(50, 40, 550, 380), filename=str(PNG))
page.insert_image(fitz.Rect(50, 400, 550, 760), filename=str(PNG))
doc.save(str(TESTDATA / "test_scan.pdf"))
doc.close()
print("[t2] 纯扫描 PDF 已生成", flush=True)

print("TEST_PDFS_DONE", flush=True)
