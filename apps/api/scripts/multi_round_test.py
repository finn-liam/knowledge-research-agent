"""多轮追问验收：同一任务连续追问 2 次，验证每轮独立报告 + SSE 完整流转。"""
import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"
ROUNDS = [
    "企业知识管理平台的 RAG 检索架构",
    "切片策略是什么",
    "向量化用的是什么模型",
]


def stream_round(client: httpx.Client, task_id: str, label: str) -> None:
    events: list[str] = []
    token_chars = 0
    with client.stream("GET", f"/api/v1/research/{task_id}/stream", timeout=300.0) as stream:
        event_name = None
        for line in stream.iter_lines():
            if line.startswith("event: "):
                event_name = line[7:]
            elif line.startswith("data: ") and event_name:
                data = json.loads(line[6:])
                if event_name == "report_token":
                    token_chars += len(data.get("delta", ""))
                events.append(event_name)
                if event_name == "stream_end":
                    break
                event_name = None
    print(f"  [{label}] stream_end=收到, token_chars={token_chars}, 事件数={len(events)}", flush=True)


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        resp = client.post("/api/v1/research", json={"query": ROUNDS[0]})
        resp.raise_for_status()
        task_id = resp.json()["task_id"]
        print(f"[created] {task_id}", flush=True)

        stream_round(client, task_id, "第1轮(提问)")
        for i, q in enumerate(ROUNDS[1:], start=2):
            r = client.post(f"/api/v1/research/{task_id}/followup", json={"query": q})
            r.raise_for_status()
            print(f"[第{i}轮追问] {q}", flush=True)
            stream_round(client, task_id, f"第{i}轮")

        detail = client.get(f"/api/v1/research/{task_id}").json()
        print(f"\n[最终] 状态={detail['status']}", flush=True)
        print(f"  messages={len(detail['messages'])} 条: {[m['content'][:12] for m in detail['messages']]}", flush=True)
        print(f"  reports={len(detail['reports'])} 个版本: {[r['version'] for r in detail['reports']]}", flush=True)
        for i, r in enumerate(detail["reports"]):
            print(f"    v{r['version']}: {len(r['markdown'])} 字 | {r['markdown'][:40]!r}", flush=True)

        ok = (
            detail["status"] == "done"
            and len(detail["messages"]) == 3
            and len(detail["reports"]) == 3
            and all(len(r["markdown"]) > 30 for r in detail["reports"])
        )
        print("MULTI_ROUND_PASS" if ok else "MULTI_ROUND_FAIL", flush=True)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
