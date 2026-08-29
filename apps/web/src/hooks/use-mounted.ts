"use client";

import { useEffect, useState } from "react";

/** 首次客户端挂载标记：用于隔离 zustand persist(localStorage) 导致的 SSR 水合不一致 */
export function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted;
}
