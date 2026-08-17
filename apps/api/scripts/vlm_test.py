"""VLM 自测：生成真实图表（matplotlib）→ describe_image 描述三类图片。

用法：python scripts/vlm_test.py
无 Key 时输出"VLM 未启用（请在 .env 填 VLM_API_KEY）"。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402

# 中文字体（避免标题渲染成方框导致 VLM 无法理解）
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

from app.core.config import get_settings  # noqa: E402

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"


def make_bar_chart(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 3.5))
    labels = ["2023", "2024", "2025"]
    values = [120, 268, 610]
    ax.bar(labels, values, color=["#8B7CF6", "#6EE7B7", "#FBBF24"])
    ax.set_title("企业 AI 知识库用户增长（万人）")
    ax.set_xlabel("年份")
    ax.set_ylabel("用户数（万人）")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(str(path), dpi=120)
    plt.close(fig)


def make_arch_diagram(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    nodes = [
        (1.5, 3, "用户提问"),
        (5, 3, "Agent 编排\n(LangGraph)"),
        (8.5, 3, "LLM 生成"),
        (5, 1, "混合检索\n(KB+论文+网页)"),
    ]
    for x, y, label in nodes:
        ax.add_patch(mpatches.FancyBboxPatch((x - 1.4, y - 0.8), 2.8, 1.6,
                                             boxstyle="round,pad=0.1",
                                             fc="#EDE9FE", ec="#7C6FF0"))
        ax.text(x, y, label, ha="center", va="center", fontsize=9)
    for (x1, y1), (x2, y2) in [((1.5, 3), (5, 3)), ((5, 3), (8.5, 3)), ((5, 3), (5, 1.8))]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="gray"))
    ax.text(5, 5.4, "Agentic RAG 架构示意图", ha="center", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(str(path), dpi=120)
    plt.close(fig)


def main() -> int:
    settings = get_settings()
    if not settings.vlm_enabled:
        print("VLM 未启用：请在 apps/api/.env 填写 VLM_API_KEY 后重跑", flush=True)
        return 1

    from app.rag.vlm import describe_image

    make_bar_chart(TESTDATA / "vlm_chart.png")
    make_arch_diagram(TESTDATA / "vlm_arch.png")
    print("[test] 已生成测试图（柱状图/架构图）", flush=True)

    for name in ("vlm_chart.png", "vlm_arch.png"):
        img_bytes = (TESTDATA / name).read_bytes()
        desc = describe_image(img_bytes)
        print(f"\n=== {name} ===", flush=True)
        print(desc or "（描述为空）", flush=True)

    # 文字截图（复用 OCR 测试图）
    img_bytes = (TESTDATA / "ocr_test.png").read_bytes()
    desc = describe_image(img_bytes)
    print(f"\n=== ocr_test.png（文字截图）===", flush=True)
    print(desc or "（描述为空）", flush=True)

    print("\nVLM_TEST_DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
