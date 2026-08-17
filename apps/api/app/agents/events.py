"""任务事件总线：LangGraph 节点 → SSE 推送的桥梁（单进程内存实现）。

每个 task_id 对应一个事件缓冲（用于断线重连快照）+ 一个订阅队列。
"""
import asyncio
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._buffers: dict[str, list[dict[str, Any]]] = {}
        self._queues: dict[str, asyncio.Queue] = {}

    def open(self, task_id: str) -> None:
        # 复用同一队列对象（不替换），避免订阅者拿到被覆盖的旧队列
        self._buffers[task_id] = []
        self._queues.setdefault(task_id, asyncio.Queue())

    def emit(self, task_id: str, event: str, data: dict[str, Any]) -> None:
        payload = {"event": event, "data": data}
        if task_id in self._buffers:
            self._buffers[task_id].append(payload)
        queue = self._queues.get(task_id)
        if queue is not None:
            queue.put_nowait(payload)

    def history(self, task_id: str) -> list[dict[str, Any]]:
        return list(self._buffers.get(task_id, []))

    def subscribe(self, task_id: str) -> asyncio.Queue:
        if task_id not in self._queues:
            self._queues[task_id] = asyncio.Queue()
        return self._queues[task_id]

    def reset(self, task_id: str) -> None:
        """追问重跑前：清空缓冲，并排空队列残留（保留同一队列对象）。"""
        self._buffers[task_id] = []
        queue = self._queues.setdefault(task_id, asyncio.Queue())
        while not queue.empty():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def close(self, task_id: str) -> None:
        self._buffers.pop(task_id, None)
        self._queues.pop(task_id, None)


EVENT_BUS = EventBus()
