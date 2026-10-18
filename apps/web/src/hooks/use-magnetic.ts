"use client";

import { useEffect, useRef } from "react";

/**
 * 磁吸效果：光标 120px 范围内元素向其偏移（max 12px），离开弹性回弹。
 * - 跟随段 0.12s 平滑（.is-near），离开段 0.35s 弹簧（.magnetic，见 globals.css）
 * - 触屏 / prefers-reduced-motion 不启用
 */
export function useMagnetic<T extends HTMLElement>(radius = 120, maxOffset = 12) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!window.matchMedia("(pointer: fine)").matches) return; // 触屏无磁吸

    const reset = () => {
      el.classList.remove("is-near");
      el.style.transform = "";
    };
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const dx = e.clientX - (r.left + r.width / 2);
      const dy = e.clientY - (r.top + r.height / 2);
      const dist = Math.hypot(dx, dy);
      if (dist >= radius) {
        if (el.classList.contains("is-near")) reset();
        return;
      }
      const strength = 1 - dist / radius; // 越近越强
      el.classList.add("is-near");
      el.style.transform = `translate(${(dx / (dist || 1)) * maxOffset * strength}px, ${
        (dy / (dist || 1)) * maxOffset * strength
      }px)`;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      el.style.transform = "";
      el.classList.remove("is-near");
    };
  }, [radius, maxOffset]);

  return ref;
}
