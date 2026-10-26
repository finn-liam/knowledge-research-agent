"use client";

import { useEffect, useRef } from "react";

/**
 * 滚动入场：观察容器内所有 .reveal 元素，进入视口（15%）一次性加 .is-in。
 * 用法：页面根调用 useReveal() 挂 ref，子元素标 .reveal（可用 style={{"--d":"60ms"}} 做 stagger）。
 * deps：列表页等"数据到达后 .reveal 才出现"的场景必须传入（如 [tasks?.length]），
 * 否则挂载时扫描不到目标，晚出现的元素永远停在 opacity:0。
 */
export function useReveal<T extends HTMLElement>(deps: unknown[] = []) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const targets: Element[] = [
      ...(root.matches(".reveal") ? [root] : []),
      ...root.querySelectorAll(".reveal:not(.is-in)"),
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 由调用方声明"可能新增 .reveal"的时机
  }, deps);

  return ref;
}
