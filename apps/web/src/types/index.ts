/** 与后端 API 对齐的 TypeScript 契约 */

export type StepStatus = "pending" | "running" | "done" | "failed" | "paused";
export type TaskStatus = "running" | "done" | "failed";
export type SourceType = "enterprise" | "paper" | "web" | "news" | "patent" | "report";

export interface StepInfo {
  step_key: string;
  label: string;
  order_index: number;
  status: StepStatus;
  meta: Record<string, unknown>;
}

export interface SourceItem {
  ref_no: number;
  type: SourceType;
  title: string;
  url: string;
  snippet: string;
  relevance: number;
  source_label: string;
  page_nos?: number[];
}

export interface GraphNode {
  id: string;
  label: string;
  group: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RunStats {
  duration_sec: number;
  sources_count: number;
  docs_processed: number;
  relevance_avg: number;
  citations_count?: number;
}

export interface ReportInfo {
  id: number;
  title: string;
  summary: string;
  markdown: string;
  version: number;
}

export interface ChatMessage {
  role: "user" | "agent";
  content: string;
}

export interface TaskDetail {
  id: string;
  title: string;
  query: string;
  status: TaskStatus;
  steps: StepInfo[];
  sources: SourceItem[];
  report: ReportInfo | null;
  reports: ReportInfo[];
  graph: GraphData;
  stats: Partial<RunStats>;
  messages: ChatMessage[];
}

export interface TaskSummary {
  id: string;
  title: string;
  query: string;
  status: TaskStatus;
  created_at: string;
}

export interface SourceStatItem {
  category: string;
  label: string;
  count: number;
}

export interface AnalyticsSummary {
  total_research: number;
  knowledge_sources: number;
  documents_processed: number;
  accuracy_rate: number;
}

/** SSE 事件载荷 */
export interface SseEvent {
  event: string;
  data: Record<string, unknown>;
}

/** 知识库文档 */
export interface KbDocument {
  id: number;
  name: string;
  doc_type: string;
  size_bytes: number;
  status: string; // pending/parsing/embedding/indexed/failed
  error_msg: string;
  chunk_count: number;
  created_at: string;
}

export interface KbChunk {
  id: number;
  chunk_index: number;
  text: string;
}

export interface KbDetail extends KbDocument {
  chunks: KbChunk[];
}

export interface KbStats {
  documents: number;
  chunks: number;
  indexed: number;
  processing: number;
  failed: number;
  vector_store_ready: boolean;
}

/** 单个知识库片段全文（来源溯源查看） */
export interface KbChunkDetail {
  document_id: number;
  document_name: string;
  chunk_index: number;
  text: string;
}
