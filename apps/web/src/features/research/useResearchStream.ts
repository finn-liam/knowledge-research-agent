import { useEffect } from "react";
import { api } from "@/lib/api";
import { useResearchStore } from "./researchStore";

const EVENT_NAMES = [
  "router_result",
  "step_started",
  "step_completed",
  "step_failed",
  "step_skipped",
  "source_found",
  "sources_final",
  "kb_status",
  "graph_updated",
  "report_token",
  "report_completed",
  "error",
  "stream_end",
] as const;

/** 完成时自动校准：用 DB 完整报告替换流式 buffer（修复流式 token 丢失导致的缺字/不完整） */
function calibrateReport(taskId: string) {
  api
    .getResearch(taskId)
    .then((d) => {
      const store = useResearchStore.getState();
      const dbMd = d.report?.markdown ?? "";
      if (!dbMd) return;
      if (dbMd.length > store.reportBuffer.length) {
        // 检测到流式缺字 → force 全量替换为 DB 完整版
        store.applySnapshot(d, true);
      }
    })
    .catch(() => undefined);
}

/** 订阅研究任务 SSE 流：
 * - phase=streaming 时连接，runNonce 变化（追问）时重连
 * - onopen（含断线重连）：拉取详情全量快照替换（报告不重复、不拼接错乱）
 * - report_completed / stream_end：自动校准为 DB 完整报告（防流式缺字）
 * - onerror + 连接关闭：拉取详情兜底，避免永久停在"处理中"
 */
export function useResearchStream() {
  const taskId = useResearchStore((s) => s.taskId);
  const phase = useResearchStore((s) => s.phase);
  const runNonce = useResearchStore((s) => s.runNonce);

  useEffect(() => {
    if (!taskId || phase !== "streaming") return;
    const es = new EventSource(api.streamUrl(taskId));
    let closed = false;

    // 连接建立（首次或重连）：拉取 DB 全量快照替换报告区
    es.onopen = () => {
      if (closed) return;
      api
        .getResearch(taskId)
        .then((d) => {
          const store = useResearchStore.getState();
          if (store.phase !== "streaming") return;
          // 只替换报告全文与统计（步骤/来源继续由增量事件驱动）
          store.applySnapshot(d);
        })
        .catch(() => undefined);
    };

    const handler = (e: MessageEvent) => {
      try {
        useResearchStore.getState().applyEvent(e.type, JSON.parse(e.data));
        // 报告完成/流结束时自动校准为 DB 完整版（防流式丢字）
        if (e.type === "report_completed" || e.type === "stream_end") {
          calibrateReport(taskId);
        }
      } catch {
        /* 忽略心跳/注释行解析异常 */
      }
    };
    for (const name of EVENT_NAMES) es.addEventListener(name, handler);

    es.onerror = () => {
      // 连接被正常关闭（cleanup）后不再兜底
      if (closed) return;
      // EventSource 已关闭（非重连中）→ 拉详情兜底
      if (es.readyState === EventSource.CLOSED) {
        closed = true;
        const store = useResearchStore.getState();
        if (store.phase !== "streaming") return;
        api
          .getResearch(taskId)
          .then((d) => {
            const st = useResearchStore.getState();
            if (st.phase !== "streaming") return;
            if (d.status === "done") {
              st.applySnapshot(d, true); // force：全量替换恢复完整报告
              st.applyEvent("stream_end", {});
            } else {
              st.setInterrupted();
            }
          })
          .catch(() => useResearchStore.getState().setInterrupted());
      }
    };

    return () => {
      closed = true;
      es.close();
    };
  }, [taskId, phase, runNonce]);
}
