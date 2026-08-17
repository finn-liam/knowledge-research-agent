"""LLM 整合验证：提问 → 检查报告是否为真实 LLM 整合输出（非摘录）。"""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        r = client.post("/api/v1/research", json={"query": "企业知识管理平台的 RAG 检索架构"})
        r.raise_for_status()
        tid = r.json()["task_id"]
        print(f"[created] {tid}", flush=True)

        with client.stream("GET", f"/api/v1/research/{tid}/stream", timeout=300.0) as stream:
            ev = None
            for line in stream.iter_lines():
                if line.startswith("event: "):
                    ev = line[7:]
                elif line.startswith("data: ") and ev:
                    data = json.loads(line[6:])
                    if ev == "report_completed":
                        print(f"[report_completed] stats={data.get('stats')}", flush=True)
                    if ev == "stream_end":
                        break
                    ev = None

        detail = client.get(f"/api/v1/research/{tid}").json()
        md = (detail.get("report") or {}).get("markdown", "")
        print(f"=== 报告长度: {len(md)} 字 ===", flush=True)
        print(md[:600], flush=True)

        # 判定：真实 LLM 整合 = 非摘录格式（不以"基于企业知识库的要点"开头、无"- "原文列表风格）
        is_excerpt = md.startswith("基于企业知识库的要点") or md.startswith("- ")
        ok = len(md) > 80 and not is_excerpt
        print(f"\n[判定] 摘录格式={is_excerpt} 长度>80={len(md) > 80}", flush=True)
        print("LLM_INTEGRATE_PASS" if ok else "LLM_INTEGRATE_FAIL", flush=True)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
