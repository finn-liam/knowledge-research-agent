"use client";

import { useEffect, useRef, useState } from "react";

/**
 * 进视口计数：元素首次进入视口时从 0 计数到 target（1.6s，easeOutQuart）。
 * - 仅触发一次（离开再进入不重复）
 * - prefers-reduced-motion / 非正值直接显示终值
 * - 所有 setState 都发生在观察器/rAF 回调内（不在 effect 体内同步调用）
 */
export function useCountUp(target: number, durationMs = 1600): {
  ref: React.RefObject<HTMLDivElement | null>;
  value: number;
} {
  const ref = useRef<HTMLDivElement>(null);
  const [value, setValue] = useState(0);
  const startedRef = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || startedRef.current) return;

    const io = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting) || startedRef.current) return;
        startedRef.current = true;
        io.disconnect();
        if (target <= 0 || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
          setValue(target);
          return;
        }
        const t0 = performance.now();
        const tick = (now: number) => {
          const p = Math.min(1, (now - t0) / durationMs);
          const eased = 1 - Math.pow(1 - p, 4); // easeOutQuart
          setValue(Math.round(target * eased));
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      },
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [target, durationMs]);

  return { ref, value };
}
