import { create } from "zustand";
import type {
  ChatMessage,
  GraphData,
  ReportInfo,
  RunStats,
  SourceItem,
  StepInfo,
  TaskDetail,
} from "@/types";

/** 与后端 STEP_DEFS 对齐（效果图2 顺序）：kb/论文/网页/报告启用，知识图谱已暂停 */
const DEFAULT_STEPS: StepInfo[] = [
  { step_key: "kb_search", label: "查询企业知识库", order_index: 0, status: "pending", meta: {} },
  { step_key: "paper_search", label: "检索学术论文", order_index: 1, status: "pending", meta: {} },
  { step_key: "web_search", label: "搜索网页信息", order_index: 2, status: "pending", meta: {} },
  { step_key: "graph_build", label: "建立知识关系图谱", order_index: 3, status: "paused", meta: {} },
  { step_key: "report_write", label: "生成分析报告", order_index: 4, status: "pending", meta: {} },
];

export type RunPhase = "idle" | "streaming" | "done" | "failed" | "interrupted";

interface ResearchState {
  taskId: string | null;
  title: string;
  query: string;
  phase: RunPhase;
  runNonce: number; // 追问重跑时 +1，驱动 SSE 重连
  steps: StepInfo[];
  sources: SourceItem[];
  graph: GraphData;
  reportBuffer: string;
  reportTitle: string;
  stats: Partial<RunStats>;
  error: string | null;
  selectedRefNo: number | null;
  messages: ChatMessage[]; // 多轮对话历史
  reports: ReportInfo[]; // 多轮报告历史（version 升序）
  snapshotLocked: boolean; // 新一轮开始后禁止 onopen 快照覆盖报告

  hydrate: (d: TaskDetail) => void;
  beginRun: (taskId: string, query: string, title: string) => void;
  applyEvent: (event: string, data: Record<string, unknown>) => void;
  applySnapshot: (d: TaskDetail, force?: boolean) => void;
  setInterrupted: () => void;
  selectSource: (refNo: number | null) => void;
}

const cloneSteps = () => DEFAULT_STEPS.map((s) => ({ ...s, meta: {} }));

// 流式节流：report_token 累积到 pending，100ms 批量刷入 reportBuffer（降低全树重渲染频率）
const FLUSH_INTERVAL_MS = 100;
let pendingTokens = "";
let flushTimer: ReturnType<typeof setTimeout> | null = null;

function scheduleFlush(set: (partial: Partial<ResearchState>) => void, get: () => ResearchState) {
  if (flushTimer) return;
  flushTimer = setTimeout(() => {
    flushTimer = null;
    if (!pendingTokens) return;
    const tokens = pendingTokens;
    pendingTokens = "";
    set({ reportBuffer: get().reportBuffer + tokens });
  }, FLUSH_INTERVAL_MS);
}

function clearFlush() {
  if (flushTimer) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }
  pendingTokens = "";
}

export const useResearchStore = create<ResearchState>((set, get) => ({
  taskId: null,
  title: "",
  query: "",
  phase: "idle",
  runNonce: 0,
  steps: cloneSteps(),
  sources: [],
  graph: { nodes: [], edges: [] },
  reportBuffer: "",
  reportTitle: "",
  stats: {},
  error: null,
  selectedRefNo: null,
  messages: [],
  reports: [],
  snapshotLocked: false,

  hydrate: (d) => {
    const running = d.status === "running";
    set({
      taskId: d.id,
      title: d.title,
      query: d.query,
      phase: running ? "streaming" : d.status === "done" ? "done" : "failed",
      runNonce: get().runNonce + 1,
      steps: d.steps.length ? d.steps : cloneSteps(),
      sources: d.sources,
      graph: d.graph,
      reportBuffer: d.report?.markdown ?? "",
      reportTitle: d.report?.title ?? "",
      stats: d.stats,
      error: null,
      selectedRefNo: null,
      messages: d.messages,
      reports: d.reports ?? [],
      snapshotLocked: false,
    });
  },

  beginRun: (taskId, query, title) => {
    clearFlush(); // 新轮开始：清空节流累积
    const messages = [...get().messages, { role: "user" as const, content: query }];
    set({
      taskId,
      query,
      title: title || get().title,
      phase: "streaming",
      runNonce: get().runNonce + 1,
      steps: cloneSteps(),
      sources: [],
      graph: { nodes: [], edges: [] },
      reportBuffer: "",
      reportTitle: "",
      stats: {},
      error: null,
      selectedRefNo: null,
      messages,
      snapshotLocked: true, // 本轮报告只能来自 SSE 流式，禁止快照覆盖
    });
  },

  applyEvent: (event, data) => {
    const state = get();
    switch (event) {
      case "router_result": {
        // 闲聊路径：检索相关步骤标为已暂停（不跑检索）
        if (data.type === "chat") {
          const pausedSteps: string[] = Array.isArray(data.paused_steps)
            ? (data.paused_steps as string[])
            : ["kb_search", "paper_search", "web_search", "graph_build"];
          set({
            steps: state.steps.map((s) =>
              pausedSteps.includes(s.step_key)
                ? { ...s, status: "paused" as StepInfo["status"], meta: {} }
                : s,
            ),
          });
        }
        break;
      }
      case "step_started":
      case "step_completed":
      case "step_failed":
      case "step_skipped": {
        const key = data.step as string;
        const status =
          event === "step_started"
            ? "running"
            : event === "step_completed"
              ? "done"
              : event === "step_skipped"
                ? "skipped"
                : "failed";
        const steps = state.steps.map((s) =>
          s.step_key === key ? { ...s, status: status as StepInfo["status"], meta: data } : s,
        );
        set({ steps });
        break;
      }
      case "source_found": {
        const item: SourceItem = {
          ref_no: 0,
          type: (data.type as SourceItem["type"]) ?? "web",
          title: String(data.title ?? ""),
          url: String(data.url ?? ""),
          snippet: String(data.snippet ?? ""),
          relevance: Number(data.relevance ?? 0),
          source_label: String(data.source_label ?? ""),
        };
        if (state.sources.some((s) => s.title === item.title)) break; // 去重
        set({ sources: [...state.sources, item] });
        break;
      }
      case "sources_final": {
        const list = (data.sources as SourceItem[]) ?? [];
        set({ sources: list });
        break;
      }
      case "graph_updated": {
        set({
          graph: {
            nodes: (data.nodes as GraphData["nodes"]) ?? [],
            edges: (data.edges as GraphData["edges"]) ?? [],
          },
        });
        break;
      }
      case "report_token": {
        // 节流：累积 60ms 批量刷新，避免每 token 触发全树重渲染
        pendingTokens += String(data.delta ?? "");
        scheduleFlush(set, get);
        break;
      }
      case "report_completed": {
        // 立即刷新剩余累积的 token
        if (pendingTokens) {
          set({ reportBuffer: state.reportBuffer + pendingTokens });
          pendingTokens = "";
        }
        clearFlush();
        // 本轮报告完成：追加到历史 reports（version 递增），解锁快照
        const newReport: ReportInfo = {
          id: Number(data.report_id ?? 0),
          title: String(data.title ?? ""),
          summary: "",
          markdown: state.reportBuffer,
          version: (state.reports.at(-1)?.version ?? 0) + 1,
        };
        set({
          phase: "done",
          reportTitle: String(data.title ?? ""),
          stats: (data.stats as RunStats) ?? {},
          reports: [...state.reports, newReport],
          snapshotLocked: false,
        });
        break;
      }
      case "error": {
        set({ phase: "failed", error: String(data.message ?? "未知错误") });
        break;
      }
      case "stream_end": {
        if (get().phase === "streaming") set({ phase: "done" });
        break;
      }
    }
  },

  selectSource: (refNo) => set({ selectedRefNo: refNo }),

  /** SSE 快照：force=true 全量替换（断线兜底）；默认保守（本轮开始后不覆盖流式报告） */
  applySnapshot: (d, force = false) => {
    const state = get();
    if (state.phase !== "streaming") return;
    const applyReport = force || !state.snapshotLocked;
    set({
      reportBuffer: applyReport && d.report?.markdown ? d.report.markdown : state.reportBuffer,
      reportTitle: d.report?.title ?? state.reportTitle,
      stats: d.stats ?? state.stats,
      sources: d.sources.length ? d.sources : state.sources,
      messages: d.messages.length ? d.messages : state.messages,
      reports: d.reports?.length ? d.reports : state.reports,
    });
  },

  /** SSE 连接中断兜底：显示"连接中断"提示，等待用户刷新或重试 */
  setInterrupted: () => set({ phase: "interrupted" }),
}));
