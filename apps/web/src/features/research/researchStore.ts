import { create } from "zustand";
import type {
  ChatMessage,
  GraphData,
  ReportInfo,
  RunStats,
  SourceItem,
  StepInfo,
  TaskDetail,
  TimelineEntry,
  TimelineKind,
} from "@/types";

/** 与后端 STEP_DEFS 对齐（效果图2 顺序）：kb/论文/网页/报告启用，知识图谱已暂停 */
const DEFAULT_STEPS: StepInfo[] = [
  { step_key: "kb_search", label: "查询本地知识库", order_index: 0, status: "pending", meta: {} },
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
  replaying: boolean; // SSE 重放中（重连/刷新后的历史回放，抑制时间线重复与报告重复追加）
  timeline: TimelineEntry[]; // 研究过程时间线（C1：Agent 思考直播，最新在底部）

  hydrate: (d: TaskDetail) => void;
  beginRun: (taskId: string, query: string, title: string) => void;
  applyEvent: (event: string, data: Record<string, unknown>) => void;
  applySnapshot: (d: TaskDetail, force?: boolean) => void;
  setInterrupted: () => void;
  selectSource: (refNo: number | null) => void;
}

const cloneSteps = () => DEFAULT_STEPS.map((s) => ({ ...s, meta: {} }));

// 时间线：入列 + 截断（只保留最近 100 条，防止长研究内存增长）
let timelineSeq = 0;
function pushTimeline(list: TimelineEntry[], kind: TimelineKind, text: string): TimelineEntry[] {
  timelineSeq += 1;
  return [...list, { id: timelineSeq, ts: Date.now(), kind, text }].slice(-100);
}

// 事件 → 时间线文案（与步骤卡中文文案风格一致）
function timelineText(event: string, data: Record<string, unknown>): { kind: TimelineKind; text: string } | null {
  const label = typeof data.label === "string" ? data.label : "";
  switch (event) {
    case "router_result": {
      const t = String(data.type ?? "knowledge");
      const mode = String(data.sources ?? "kb_only");
      if (t === "chat") return { kind: "router", text: "意图识别：闲聊，跳过检索直接回答" };
      return mode === "multi"
        ? { kind: "router", text: "意图识别：知识问题，三路全开（知识库 ∥ 论文 ∥ 网页）" }
        : { kind: "router", text: "意图识别：知识问题，先查本地知识库（渐进式）" };
    }
    case "step_started":
      return { kind: "step_started", text: `${label || "步骤"} · 开始` };
    case "step_completed": {
      const hits = data.hits;
      return {
        kind: "step_completed",
        text:
          typeof hits === "number"
            ? `${label || "步骤"} · 完成（命中 ${hits} 条）`
            : `${label || "步骤"} · 完成`,
      };
    }
    case "step_failed":
      return { kind: "step_failed", text: `${label || "步骤"} · 失败` };
    case "step_skipped":
      return { kind: "step_skipped", text: `${label || "步骤"} · 跳过` };
    case "sources_final": {
      const n = Array.isArray(data.sources) ? data.sources.length : 0;
      return n > 0
        ? { kind: "sources", text: `来源融合：${n} 条候选进入质量评判` }
        : null;
    }
    case "grade_result": {
      const grades = Array.isArray(data.grades) ? data.grades : [];
      const high = grades.filter(
        (g) => typeof (g as Record<string, unknown>)?.score === "number" &&
          ((g as Record<string, unknown>).score as number) >= 0.6,
      ).length;
      const low = grades.filter(
        (g) => typeof (g as Record<string, unknown>)?.score === "number" &&
          ((g as Record<string, unknown>).score as number) < 0.4,
      ).length;
      return { kind: "grade", text: `质量评判：${grades.length} 条中高分 ${high} 条、低分 ${low} 条` };
    }
    case "rewrite": {
      const q = String(data.query ?? "");
      return { kind: "rewrite", text: `反思重查：改写问题为「${q.slice(0, 40)}${q.length > 40 ? "…" : ""}」` };
    }
    case "report_completed": {
      const stats = (data.stats ?? {}) as Record<string, unknown>;
      const n = typeof stats.sources_count === "number" ? stats.sources_count : 0;
      return { kind: "report_done", text: `报告生成完成（基于 ${n} 条来源）` };
    }
    case "error":
      return { kind: "error", text: `流程错误：${String(data.message ?? "未知")}` };
    default:
      return null;
  }
}

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
  replaying: false,
  timeline: [],

  hydrate: (d) => {
    const running = d.status === "running";
    // 失败任务恢复真实错误原因（后端 on_error 持久化在 stats_json.error）
    const statsAny = (d.stats ?? {}) as Record<string, unknown>;
    const savedError = typeof statsAny.error === "string" ? statsAny.error : null;
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
      error: savedError,
      selectedRefNo: null,
      messages: d.messages,
      reports: d.reports ?? [],
      snapshotLocked: false,
      timeline: [],
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
      replaying: false,
      timeline: [{ id: ++timelineSeq, ts: Date.now(), kind: "router", text: "新问题已提交，开始研究" }],
    });
  },

  applyEvent: (event, data) => {
    // 时间线：重放期间（重连/刷新后的历史回放）不入列，避免重复条目
    if (!get().replaying) {
      const tl = timelineText(event, data);
      if (tl) set({ timeline: pushTimeline(get().timeline, tl.kind, tl.text) });
    }

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
      case "report_reset": {
        // 重放协议：历史含 report_token，先清空缓冲再按序重建（重连/刷新后文本无破洞）
        if (get().phase === "streaming") {
          clearFlush();
          set({ reportBuffer: "" });
        }
        break;
      }
      case "replay_end": {
        if (get().replaying) set({ replaying: false });
        break;
      }
      case "report_completed": {
        // 立即刷新剩余累积的 token（必须取最新 buffer——顶部捕获的 state 是旧快照，
        // 旧实现导致入库报告缺最后一段 token）
        const freshBuffer = get().reportBuffer + pendingTokens;
        pendingTokens = "";
        clearFlush();
        const rid = Number(data.report_id ?? 0);
        // 重放去重：同一报告（report_id 相同）不重复追加版本
        const already = rid > 0 && state.reports.some((r) => r.id === rid);
        const newReport: ReportInfo = {
          id: rid,
          title: String(data.title ?? ""),
          summary: "",
          markdown: freshBuffer,
          version: (state.reports.at(-1)?.version ?? 0) + 1,
        };
        set({
          phase: "done",
          reportBuffer: freshBuffer,
          reportTitle: String(data.title ?? ""),
          stats: (data.stats as RunStats) ?? {},
          reports: already ? state.reports : [...state.reports, newReport],
          snapshotLocked: false,
          replaying: false,
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

  /** SSE 快照：force=true 全量替换（断线兜底 + 完成时校准）；默认保守（本轮开始后不覆盖流式报告） */
  applySnapshot: (d, force = false) => {
    const state = get();
    // force 校准允许在 done 阶段执行：report_completed 已把 phase 切成 done，
    // 异步校准返回时若仍拦在 streaming 守卫外，"完成校准"永远不会生效
    if (state.phase !== "streaming" && !force) return;
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
