"""在进程内直接复现图执行错误，打印完整堆栈。"""
import asyncio
import time
import traceback

from app.agents.graph import get_research_graph


async def main() -> None:
    graph = get_research_graph()
    try:
        result = await graph.ainvoke(
            {
                "task_id": "repro-direct",
                "query": "分析某技术方向未来趋势。",
                "metrics": {"t0": time.time()},
                "errors": [],
            }
        )
        print("OK keys:", sorted(result.keys()))
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
