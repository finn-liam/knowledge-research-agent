"""KB RAG 验收：研究提问 → 校验知识库步骤返回真实企业来源。"""
import json
import os
import re
import sys
import time

import httpx

BASE = os.environ.get("KRA_BASE", "http://127.0.0.1:8000")
QUERY = "企业知识管理平台的 RAG 检索架构与切片策略"

with httpx.Client(base_url=BASE, timeout=30.0) as client:
    resp = client.post("/api/v1/research", json={"query": QUERY})
    resp.raise_for_status()
    task_id = resp.json()["task_id"]
    print(f"[created] {task_id}", flush=True)

    kb_hits = []
    t0 = time.time()
    with client.stream("GET", f"/api/v1/research/{task_id}/stream", timeout=300.0) as stream:
        event_name = None
        for line in stream.iter_lines():
            if line.startswith("event: "):
                event_name = line[7:]
            elif line.startswith("data: ") and event_name:
                data = json.loads(line[6:])
                if event_name == "source_found" and data.get("type") == "enterprise":
                    kb_hits.append((data.get("title", ""), data.get("relevance", 0)))
                if event_name == "stream_end":
                    break
                event_name = None
    print(f"[stream done] {time.time() - t0:.1f}s", flush=True)

    detail = client.get(f"/api/v1/research/{task_id}").json()
    enterprise = [s for s in detail["sources"] if s["type"] == "enterprise"]
    print(f"[kb sources in SSE] {len(kb_hits)}", flush=True)
    for t, r in kb_hits:
        print(f"   SSE: {t}  rel={r}", flush=True)
    print(f"[kb sources in final] {len(enterprise)}", flush=True)
    for s in enterprise:
        print(f"   FINAL: [{s['ref_no']}] {s['title']}  rel={s['relevance']}", flush=True)
    simulated = [s for s in enterprise if s.get("url", "").startswith("kb://internal")]
    print(f"[simulated count] {len(simulated)}", flush=True)
    ok = len(enterprise) >= 1 and len(simulated) == 0 and detail["status"] == "done"
    print("KB_RAG_PASS" if ok else "KB_RAG_FAIL", flush=True)
