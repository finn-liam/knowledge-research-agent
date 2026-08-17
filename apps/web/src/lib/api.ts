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

  streamUrl: (taskId: string) => `${BASE}/research/${taskId}/stream`,

  // ---------- 知识库 ----------
  uploadDocuments: async (files: File[]) => {
    const form = new FormData();
    for (const f of files) form.append("files", f);
    const resp = await fetch(`${BASE}/documents`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(`上传失败: ${resp.status}`);
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
