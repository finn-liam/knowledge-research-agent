/** 数字千分位：1245 -> "1,245" */
export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

/** 相对时间：刚刚 / n分钟前 / n小时前 / n天前 */
export function relativeTime(iso: string): string {
  if (!iso) return "";
  const then = parseIsoTime(iso);
  const diff = Math.max(0, Date.now() - then);
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  return `${days} 天前`;
}

/** 解析时间字符串：无时区标记时按 UTC 处理（后端时间均为 UTC，防止被按本地时区误解析） */
function parseIsoTime(iso: string): number {
  const hasTzMarker = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasTzMarker ? iso : `${iso}Z`).getTime();
}

/** 秒 -> "2分 34秒" */
export function formatDuration(sec: number): string {
  if (!sec) return "0 秒";
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return m > 0 ? `${m} 分 ${s} 秒` : `${s} 秒`;
}

/** 相关度 0~1 -> 百分比文本 */
export function formatRelevance(v: number): string {
  return `${Math.round(v * 100)}%`;
}
