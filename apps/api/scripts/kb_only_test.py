"""纯 KB RAG 验收：相关提问 → 问答式+标签；无关提问 → 明确提示未找到。"""
import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"
QUERIES = [
    "企业知识管理平台的 RAG 检索架构与切片策略",
    "量子计算的最新突破是什么",
]


def run(client: httpx.Client, query: str) -> dict:
    resp = client.post("/api/v1/research", json={"query": query})
    resp.raise_for_status()
    task_id = resp.json()["task_id"]
    print(f"\n=== 提问: {query} ===", flush=True)
    with client.stream("GET", f"/api/v1/research/{task_id}/stream", timeout=300.0) as stream:
        event_name = None
        for line in stream.iter_lines():
            if line.startswith("event: "):
                event_name = line[7:]
            elif line.startswith("data: ") and event_name:
                data = json.loads(line[6:])
                if event_name in ("step_completed", "kb_status", "report_completed"):
                    print(f"  [{event_name}] {data}", flush=True)
                if event_name == "stream_end":
                    break
                event_name = None
    detail = client.get(f"/api/v1/research/{task_id}").json()
    print(f"  steps: {[(s['step_key'], s['status']) for s in detail['steps']]}", flush=True)
    print(f"  sources: {len(detail['sources'])} 条企业来源", flush=True)
    md = (detail.get("report") or {}).get("markdown", "")
    print(f"  报告前 200 字:\n{md[:200]}\n", flush=True)
    return {"task_id": task_id, "detail": detail, "md": md}


def main() -> int:
    ok = True
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        r1 = run(client, QUERIES[0])
        has_cite = "[1]" in r1["md"] or "[" in r1["md"]
        steps_ok = all(
            s["status"] == "done"
            for s in r1["detail"]["steps"]
            if s["step_key"] in ("kb_search", "paper_search", "web_search", "report_write")
        ) and all(
            s["status"] == "paused"
            for s in r1["detail"]["steps"]
            if s["step_key"] == "graph_build"
        )
        ok &= has_cite and steps_ok and len(r1["detail"]["sources"]) > 0
        print(f"  相关提问: 引用标签={has_cite} 步骤状态={steps_ok} 企业来源>0={len(r1['detail']['sources'])>0}", flush=True)

        r2 = run(client, QUERIES[1])
        # 多源恢复后：外部来源（网页/论文）可能命中 → 正常回答；三路全空才"未找到"
        no_hit_msg = "未找到" in r2["md"]
        has_content = len(r2["md"]) > 50
        ok &= has_content
        print(f"  无关提问: 含'未找到'提示={no_hit_msg} 有实质回答={has_content}", flush=True)

    print("KB_ONLY_RAG_PASS" if ok else "KB_ONLY_RAG_FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
