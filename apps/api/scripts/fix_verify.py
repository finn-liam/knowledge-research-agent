"""完整链路验证：提问 Hello Agents 是什么 → 检查企业知识库来源是否参与。"""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        r = client.post("/api/v1/research", json={"query": "Hello Agents 是什么"})
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
                    if ev == "step_completed":
                        print(f"  step: {data.get('label')} hits={data.get('hits')} status={data.get('kb_status')}", flush=True)
                    if ev == "stream_end":
                        break
                    ev = None

        detail = client.get(f"/api/v1/research/{tid}").json()
        by: dict[str, int] = {}
        for src in detail["sources"]:
            by[src["type"]] = by.get(src["type"], 0) + 1
        print(f"[sources 按类型] {by}", flush=True)
        for src in detail["sources"][:4]:
            print(f"  {src['type']:10s} | {src['title'][:46]} | rel={src['relevance']}", flush=True)
        md = (detail.get("report") or {}).get("markdown", "")
        print(f"[报告] {len(md)} 字", flush=True)
        print(md[:220], flush=True)

        ok = by.get("enterprise", 0) > 0 and len(md) > 80
        print("FULL_CHAIN_PASS" if ok else "FULL_CHAIN_FAIL", flush=True)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
