import type {
  AnalyticsSummary,
  KbChunkDetail,
  KbDetail,
  KbDocument,
  KbStats,
  SourceStatItem,
  TaskDetail,
  TaskSummary,
} from "@/types";

const BASE = "/api/v1";

// SSE 直连后端：Next dev 代理会缓冲 SSE 流（实测 317 个 token 全部在 26.8s 时
// 一簇到达、且丢事件导致报告缺字）。NEXT_PUBLIC_SSE_BASE 留空则同源走代理
// （生产 standalone），开发环境在 .env.development 里直连 127.0.0.1:8900。
const SSE_BASE = process.env.NEXT_PUBLIC_SSE_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`API ${resp.status}: ${await resp.text()}`);
  }
  return resp.json() as Promise<T>;
}

// 上传失败时读出 FastAPI 错误体 {"detail": "..."}（不支持的类型/超限等 422 原因），
// 非 JSON 响应（如后端未启动时代理层 404/502）回退到裸状态码
async function uploadError(resp: Response): Promise<string> {
  try {
    const body = (await resp.json()) as { detail?: string };
    if (body?.detail) return `上传失败: ${body.detail}`;
  } catch {
    // 非 JSON 响应，走状态码
  }
  return `上传失败: ${resp.status}`;
}

export const api = {
  createResearch: (query: string, lang: string = "zh") =>
    request<{ task_id: string; title: string }>("/research", {
      method: "POST",
      body: JSON.stringify({ query, lang }),
    }),

  listResearch: (limit = 20) => request<TaskSummary[]>(`/research?limit=${limit}`),

  getResearch: (taskId: string) => request<TaskDetail>(`/research/${taskId}`),

  followup: (taskId: string, query: string, lang: string = "zh") =>
    request<{ ok: boolean }>(`/research/${taskId}/followup`, {
      method: "POST",
      body: JSON.stringify({ query, lang }),
    }),

  sourceStats: () => request<{ items: SourceStatItem[] }>("/sources/stats"),

  analyticsSummary: () => request<AnalyticsSummary>("/analytics/summary"),

  exportUrl: (taskId: string) => `${BASE}/research/${taskId}/export`,

  streamUrl: (taskId: string) => `${SSE_BASE}${BASE}/research/${taskId}/stream`,

  // ---------- 知识库 ----------
  uploadDocuments: async (files: File[]) => {
    const form = new FormData();
    for (const f of files) form.append("files", f);
    const resp = await fetch(`${BASE}/documents`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(await uploadError(resp));
    return resp.json() as Promise<{ items: { id: number; name: string }[] }>;
  },

  listDocuments: () => request<KbDocument[]>("/documents"),

  getDocument: (id: number) => request<KbDetail>(`/documents/${id}`),

  deleteDocument: (id: number) =>
    request<{ ok: boolean }>(`/documents/${id}`, { method: "DELETE" }),

  kbStats: () => request<KbStats>("/kb/stats"),

  kbChunk: (documentId: number, chunkIndex: number) =>
    request<KbChunkDetail>(`/kb/chunk?document_id=${documentId}&chunk_index=${chunkIndex}`),
};
