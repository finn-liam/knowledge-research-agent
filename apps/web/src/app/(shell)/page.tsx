"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { GraphMiniPanel } from "@/components/graph/GraphMiniPanel";
import { RightPanel } from "@/components/layout/RightPanel";
import { ExampleCards } from "@/components/research/ExampleCards";
import { ResearchComposer } from "@/components/research/ResearchComposer";
import { SourcesStatsPanel } from "@/components/sources/SourcesStatsPanel";
import { ResearchStatsPanel } from "@/components/stats/ResearchStatsPanel";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUserStore } from "@/features/user/userStore";
import { api } from "@/lib/api";

/** 首页：欢迎区 + 研究输入框 + 示例卡片 + 右侧三面板（对齐效果图1） */
export default function HomePage() {
  const router = useRouter();
  const reportLang = useUserStore((s) => s.reportLang);

  const { data: sourceStats } = useQuery({
    queryKey: ["source-stats"],
    queryFn: api.sourceStats,
  });
  const { data: summary } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: api.analyticsSummary,
  });

  const startResearch = async (query: string) => {
    try {
      const { task_id } = await api.createResearch(query, reportLang);
      router.push(`/research/${task_id}`);
    } catch (e) {
      // 创建失败（后端不可达/校验拒绝）时给出反馈，避免"点了没反应"
      window.alert(`研究任务创建失败，请稍后重试。\n${e instanceof Error ? e.message : e}`);
    }
  };

  return (
    <>
      <ScrollArea className="min-w-0 flex-1">
        <div className="mx-auto max-w-[860px] px-5 pb-20 pt-10 md:px-8 md:pt-20">
          {/* 欢迎区：左对齐编辑式排版（eyebrow → 48px 主标 → 说明），逐行遮罩上浮入场 */}
          <div>
            <div
              className="reveal-line text-[11px] font-medium uppercase tracking-[0.22em] text-muted-foreground/70"
              style={{ "--d": "0ms" } as React.CSSProperties}
            >
              Agentic RAG · Multi-Source · Cited
            </div>
            <h1
              className="reveal-line mt-3 max-w-[640px] text-[34px] font-bold leading-[1.1] tracking-[-0.025em] sm:text-[44px] md:text-[48px] md:leading-[1.06]"
              style={{ "--d": "80ms" } as React.CSSProperties}
            >
              问一个问题，
              <br />
              追踪全部证据。
            </h1>
            <p
              className="reveal-line mt-4 max-w-[520px] text-[15px] leading-relaxed text-muted-foreground"
              style={{ "--d": "160ms" } as React.CSSProperties}
            >
              多源检索、质量判断与反思重查自动完成，给出带引用溯源的研究报告
            </p>
          </div>

          {/* 研究输入框 */}
          <div className="reveal-line mt-7 md:mt-9" style={{ "--d": "240ms" } as React.CSSProperties}>
            <ResearchComposer variant="hero" onSubmit={startResearch} />
          </div>

          {/* 示例问题：小写字距标签 + 双列卡片（移动端单列） */}
          <div className="reveal-line mt-10 md:mt-16" style={{ "--d": "320ms" } as React.CSSProperties}>
            <div className="mb-4 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground/70">
              Try these examples
            </div>
            <ExampleCards onPick={startResearch} />
          </div>
        </div>
      </ScrollArea>

      <RightPanel>
        <SourcesStatsPanel items={sourceStats?.items ?? []} />
        <GraphMiniPanel
          graph={{ nodes: [], edges: [] }}
          hint="完成首次研究后，实体与关系将在这里连成图谱"
        />
        <ResearchStatsPanel summary={summary} />
      </RightPanel>
    </>
  );
}
