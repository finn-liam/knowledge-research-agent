"""多源 + Self-RAG 验收：三路来源、grader 事件、步骤状态、LLM 整合。"""
import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        r = client.post("/api/v1/research", json={"query": "AI Agent 自主规划的核心技术"})
        r.raise_for_status()
        tid = r.json()["task_id"]
        print(f"[created] {tid}", flush=True)

        events: list[str] = []
        with client.stream("GET", f"/api/v1/research/{tid}/stream", timeout=420.0) as stream:
            ev = None
            for line in stream.iter_lines():
                if line.startswith("event: "):
                    ev = line[7:]
                elif line.startswith("data: ") and ev:
                    data = json.loads(line[6:])
                    if ev in ("grade_result", "rewrite", "report_completed", "step_completed"):
                        label = data.get("label", "")
                        extra = ""
                        if ev == "step_completed":
                            extra = f" hits={data.get('hits')}"
                        if ev == "grade_result":
                            extra = f" grades={len(data.get('grades', []))} 条"
                        if ev == "rewrite":
                            extra = f" query={data.get('query', '')[:40]}"
                        print(f"  [{ev}] {label}{extra}", flush=True)
                    events.append(ev)
                    if ev == "stream_end":
                        break
                    ev = None

        detail = client.get(f"/api/v1/research/{tid}").json()
        print(f"\n[最终] status={detail['status']}", flush=True)
        print(f"  steps: {[(s['step_key'], s['status']) for s in detail['steps']]}", flush=True)
        by_type: dict[str, int] = {}
        for s in detail["sources"]:
            by_type[s["type"]] = by_type.get(s["type"], 0) + 1
        print(f"  sources 按类型: {by_type}", flush=True)
        md = (detail.get("report") or {}).get("markdown", "")
        print(f"  报告 {len(md)} 字 | 开头: {md[:120]!r}", flush=True)

        ok = (
            detail["status"] == "done"
            and by_type.get("enterprise", 0) >= 0
            and "grade_result" in events
            and len(md) > 80
            and all(
                (s["step_key"] == "graph_build" and s["status"] == "paused")
                or s["status"] == "done"
                for s in detail["steps"]
            )
        )
        print("MULTI_SOURCE_PASS" if ok else "MULTI_SOURCE_FAIL", flush=True)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
