"""后端冒烟测试：创建研究任务 → 抓取 SSE 事件流 → 核对详情落库。"""
import json
import os
import sys
import time

import httpx

BASE = os.environ.get("KRA_BASE", "http://127.0.0.1:8000")
QUERY = "分析某技术方向未来趋势。"


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        try:
            health = client.get("/health").json()
        except Exception:
            health = {"note": "health endpoint not proxied, skip"}
        print(f"[health] {health}")

        resp = client.post("/api/v1/research", json={"query": QUERY})
        resp.raise_for_status()
        task = resp.json()
        task_id = task["task_id"]
        print(f"[created] {task}")

        events: list[str] = []
        report_chars = 0
        t0 = time.time()
        with client.stream(
            "GET", f"/api/v1/research/{task_id}/stream", timeout=300.0
        ) as stream:
            event_name = None
            for line in stream.iter_lines():
                if line.startswith("event: "):
                    event_name = line[7:]
                elif line.startswith("data: ") and event_name:
                    data = json.loads(line[6:])
                    if event_name == "report_token":
                        report_chars += len(data.get("delta", ""))
                    else:
                        label = data.get("label") or data.get("title") or ""
                        extra = f" hits={data['hits']}" if "hits" in data else ""
                        print(f"  [sse] {event_name:<16} {label}{extra}", flush=True)
                    events.append(event_name)
                    if event_name == "stream_end":
                        break
                    event_name = None

        elapsed = time.time() - t0
        print(f"[stream done] {elapsed:.1f}s, report_tokens_chars={report_chars}")

        detail = client.get(f"/api/v1/research/{task_id}").json()
        print(f"[detail] status={detail['status']} title={detail['title']}")
        print(f"[detail] steps={[ (s['step_key'], s['status']) for s in detail['steps'] ]}")
        print(f"[detail] sources={len(detail['sources'])} "
              f"types={sorted({s['type'] for s in detail['sources']})}")
        print(f"[detail] graph_nodes={len(detail['graph'].get('nodes', []))} "
              f"edges={len(detail['graph'].get('edges', []))}")
        print(f"[detail] stats={detail['stats']}")
        md = (detail.get("report") or {}).get("markdown", "")
        import re
        cites = sorted({int(n) for n in re.findall(r"\[(\d+)\]", md)})
        print(f"[report] len={len(md)} citations_used={cites}")
        print(f"[report] first120={md[:120]!r}")

        stats = client.get("/api/v1/sources/stats").json()
        print(f"[source_stats] {[(i['label'], i['count']) for i in stats['items']]}")
        summary = client.get("/api/v1/analytics/summary").json()
        print(f"[analytics] {summary}")

        ok = (
            detail["status"] == "done"
            and len(detail["sources"]) >= 8
            and len(detail["graph"].get("nodes", [])) >= 6
            and len(md) > 400
            and "stream_end" in events
        )
        print("SMOKE_TEST_PASS" if ok else "SMOKE_TEST_FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
