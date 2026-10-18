"use client";

import { useEffect, useRef } from "react";

/**
 * 滚动入场：观察容器内所有 .reveal 元素，进入视口（15%）一次性加 .is-in。
 * 用法：页面根调用 useReveal() 挂 ref，子元素标 .reveal（可用 style={{"--d":"60ms"}} 做 stagger）。
 */
export function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const targets: Element[] = [
      ...(root.matches(".reveal") ? [root] : []),
      ...root.querySelectorAll(".reveal"),
    ];
    if (!targets.length) return;

    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("is-in");
            io.unobserve(e.target); // 一次性：离开不重复
          }
        }
      },
      { threshold: 0.15 },
    );
    targets.forEach((t) => io.observe(t));
    return () => io.disconnect();
  }, []);

  return ref;
}
