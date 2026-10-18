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
        <div className="mx-auto max-w-[860px] px-8 pb-16 pt-14">
          {/* 欢迎区：排印层级（eyebrow → 44px 主标 → 说明），主色只留给活物 */}
          <div className="text-center">
            <div className="text-[11px] font-medium uppercase tracking-[0.22em] text-muted-foreground/70">
              Agentic RAG · Multi-Source · Cited
            </div>
            <h1 className="mt-3 text-[44px] font-bold leading-[1.08] tracking-[-0.02em]">
              Knowledge Research Agent
            </h1>
            <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground">
              问一个问题，自动完成多源检索、质量判断与反思重查，给出带引用溯源的研究报告
            </p>
          </div>

          {/* 研究输入框 */}
          <div className="mt-8">
            <ResearchComposer variant="hero" onSubmit={startResearch} />
          </div>

          {/* 示例问题 */}
          <div className="mt-10">
            <div className="mb-3.5 text-center text-sm font-medium text-muted-foreground">
              Try these examples
            </div>
            <ExampleCards onPick={startResearch} />
          </div>
        </div>
      </ScrollArea>

      <RightPanel>
        <SourcesStatsPanel items={sourceStats?.items ?? []} />
        <GraphMiniPanel graph={{ nodes: [], edges: [] }} />
        <ResearchStatsPanel summary={summary} />
      </RightPanel>
    </>
  );
}
