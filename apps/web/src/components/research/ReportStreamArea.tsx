"use client";

import { memo, useEffect, useRef } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { useResearchStore } from "@/features/research/researchStore";
import { ReportViewer } from "./ReportViewer";

/** 报告流式区：单独订阅 reportBuffer —— 打字机 30ms/帧的更新只重渲染本区，
 * 研究页其余部分（步骤卡/来源面板/输入框/时间线）不再随之重渲染。 */
export const ReportStreamArea = memo(function ReportStreamArea() {
  const phase = useResearchStore((s) => s.phase);
  const reportBuffer = useResearchStore((s) => s.reportBuffer);
  const lastReportMd = useResearchStore((s) => s.reports.at(-1)?.markdown ?? "");

  const streaming = phase === "streaming";
  // 当前轮报告：流式中只用本轮 buffer；完成后 buffer 为空才回退最后一版
  const currentReport = streaming ? reportBuffer : reportBuffer || lastReportMd;

  // 流式自动滚动：节流 200ms + 仅当用户停留在底部时跟随（上翻阅读不打扰）
  const endRef = useRef<HTMLDivElement>(null);
  const lastScrollAt = useRef(0);
  useEffect(() => {
    if (!streaming || !reportBuffer) return;
    const now = Date.now();
    if (now - lastScrollAt.current < 200) return;
    lastScrollAt.current = now;
    const anchor = endRef.current;
    if (!anchor) return;
    const vp = anchor.closest?.("[data-radix-scroll-area-viewport]") as HTMLElement | null;
    if (vp && vp.scrollTop + vp.clientHeight < vp.scrollHeight - 140) return; // 用户上翻中
    anchor.scrollIntoView({ behavior: "auto", block: "end", inline: "nearest" });
    if (window.scrollX !== 0) window.scrollTo({ left: 0 });
  }, [reportBuffer, streaming]);

  return (
    <>
      {currentReport ? (
        <ReportViewer markdown={currentReport} streaming={streaming} />
      ) : (
        streaming && (
          <div className="space-y-2.5 pt-2">
            <Skeleton className="h-5 w-2/5" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-4/5" />
          </div>
        )
      )}
      {/* 流式自动滚动定位锚点 */}
      <div ref={endRef} />
    </>
  );
});
