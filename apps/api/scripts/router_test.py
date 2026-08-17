"""验证：闲聊路由（你好 → chat，不检索）+ 知识问题（原流程不回归）。"""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"


def run(client: httpx.Client, query: str) -> dict:
    r = client.post("/api/v1/research", json={"query": query})
    r.raise_for_status()
    tid = r.json()["task_id"]
    events: list[str] = []
    tokens = ""
    with client.stream("GET", f"/api/v1/research/{tid}/stream", timeout=300.0) as stream:
        ev = None
        for line in stream.iter_lines():
            if line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: ") and ev:
                data = json.loads(line[6:])
                if ev == "router_result":
                    print(f"  [router] type={data.get('type')}", flush=True)
                if ev == "report_token":
                    tokens += data.get("delta", "")
                events.append(ev)
                if ev == "stream_end":
                    break
                ev = None
    detail = client.get(f"/api/v1/research/{tid}").json()
    return {"events": events, "tokens": tokens, "detail": detail}


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        print("=== 测试1: 你好（应走 chat，不检索）===", flush=True)
        r1 = run(client, "你好")
        has_router = "router_result" in r1["events"]
        # 检索步骤（kb/paper/web）不应启动：检查这些步骤的 step_started 事件
        kb_steps = {s["step_key"]: s["status"] for s in r1["detail"]["steps"]}
        kb_retrieved = any(kb_steps.get(k) != "paused" for k in ("kb_search", "paper_search", "web_search"))
        print(f"  router事件: {has_router} | 检索步骤已暂停: {not kb_retrieved}", flush=True)
        print(f"  回复: {r1['tokens'][:60]}", flush=True)
        print(f"  步骤状态: {kb_steps}", flush=True)

        print("=== 测试2: 员工年假怎么计算（应走正常检索）===", flush=True)
        r2 = run(client, "员工年假怎么计算")
        kb_ok = len(r2["tokens"]) > 100
        print(f"  回复长度: {len(r2['tokens'])}", flush=True)
        print(f"  回复开头: {r2['tokens'][:60]}", flush=True)

        chat_ok = has_router and not kb_retrieved and "未找到" not in r1["tokens"] and len(r1["tokens"]) > 5
        print("\nROUTER_CHAT_PASS" if chat_ok and kb_ok else "ROUTER_CHAT_FAIL", flush=True)
        return 0 if (chat_ok and kb_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
