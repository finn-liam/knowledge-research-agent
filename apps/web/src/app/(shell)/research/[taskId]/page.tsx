"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { GraphMiniPanel } from "@/components/graph/GraphMiniPanel";
import { RightPanel } from "@/components/layout/RightPanel";
import { AgentHeader } from "@/components/research/AgentHeader";
import { AgentStepCards } from "@/components/research/AgentStepCards";
import { Disclaimer } from "@/components/research/Disclaimer";
import { ProcessTimeline } from "@/components/research/ProcessTimeline";
import { ReportHeader } from "@/components/research/ReportHeader";
import { ReportStreamArea } from "@/components/research/ReportStreamArea";
import { ReportViewer } from "@/components/research/ReportViewer";
import { ResearchComposer } from "@/components/research/ResearchComposer";
import { UserBubble } from "@/components/research/UserBubble";
import { SourcesPanel } from "@/components/sources/SourcesPanel";
import { RunStatsPanel } from "@/components/stats/RunStatsPanel";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useResearchStore } from "@/features/research/researchStore";
import { useResearchStream } from "@/features/research/useResearchStream";
import { useUserStore } from "@/features/user/userStore";
import { api } from "@/lib/api";

/** 研究报告页：多轮对话流 + 当前轮步骤卡 + 流式报告 + 右侧面板（对齐效果图2）

 * 渲染分层（性能关键）：页面只订阅低频字段（步骤/来源/消息/面板数据），
 * 打字机 30ms/帧的 reportBuffer 更新被隔离在 ReportStreamArea 内——
 * 流式期间本页与其余子树（输入框/来源面板/时间线）不重渲染。
 */
export default function ResearchPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const phase = useResearchStore((s) => s.phase);
  const steps = useResearchStore((s) => s.steps);
  const sources = useResearchStore((s) => s.sources);
  const graph = useResearchStore((s) => s.graph);
  const stats = useResearchStore((s) => s.stats);
  const messages = useResearchStore((s) => s.messages);
  const reports = useResearchStore((s) => s.reports);
  const headerTitle = useResearchStore((s) => s.reportTitle || s.title);
  const error = useResearchStore((s) => s.error);
  const streaming = phase === "streaming";

  // 挂载/换任务：拉取详情并水合 store（运行中任务随后由 SSE 接管）
  useEffect(() => {
    if (!taskId || taskId === useResearchStore.getState().taskId) return;
    api
      .getResearch(taskId)
      .then((d) => useResearchStore.getState().hydrate(d))
      .catch(() => useResearchStore.setState({ phase: "failed", error: "任务加载失败" }));
  }, [taskId]);

  useResearchStream();

  const followup = async (query: string) => {
    if (!taskId) return;
    const lang = useUserStore.getState().reportLang;
    try {
      await api.followup(taskId, query, lang);
      useResearchStore.getState().beginRun(taskId, query, useResearchStore.getState().title);
    } catch (e) {
      // 追问提交失败（含任务仍在运行中的 409）时给出反馈
      window.alert(`追问提交失败，请稍后重试。\n${e instanceof Error ? e.message : e}`);
    }
  };

  const lastMsgIndex = Math.max(0, messages.length - 1);

  return (
    <>
      <div className="flex min-w-0 flex-1 flex-col">
        <ReportHeader
          title={headerTitle}
          taskId={taskId ?? null}
          canExport={phase === "done"}
        />

        <ScrollArea className="min-h-0 flex-1">
          <div className="mx-auto max-w-[860px] space-y-8 px-4 py-8 md:px-8">
            {/* 多轮对话：每轮 = 用户气泡 + Agent 报告块 */}
            {messages.map((msg, i) => {
              const isLast = i === lastMsgIndex;
              const report = i < reports.length ? reports[i].markdown : null;
              return (
                <div key={i} className="space-y-4">
                  <UserBubble content={msg.content} />
                  {isLast ? (
                    <div className="space-y-4">
                      <AgentHeader phase={phase} />
                      <AgentStepCards steps={steps} />
                      <ProcessTimeline />

                      {phase === "failed" && (
                        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
                          研究过程出现错误：{error ?? "未知错误"}，请重试。
                        </div>
                      )}

                      {phase === "interrupted" && (
                        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                          连接中断，研究可能未完成。请刷新页面查看最终结果，或重新提问。
                        </div>
                      )}

                      {/* 当前轮报告（骨架屏/流式打字机/完成回退）自治渲染 + 自动滚动 */}
                      <ReportStreamArea />
                    </div>
                  ) : (
                    report && (
                      <div className="space-y-4">
                        <AgentHeader phase="done" />
                        <ReportViewer markdown={report} streaming={false} />
                      </div>
                    )
                  )}
                </div>
              );
            })}
          </div>
        </ScrollArea>

        <div className="border-t bg-background px-4 pb-2 pt-3 md:px-8">
          <div className="mx-auto max-w-[860px]">
            <ResearchComposer
              variant="followup"
              onSubmit={followup}
              disabled={streaming}
            />
            <Disclaimer />
          </div>
        </div>
      </div>

      <RightPanel>
        <SourcesPanel sources={sources} />
        <GraphMiniPanel graph={graph} hint="知识图谱功能暂缓，将在后续版本启用" />
        <RunStatsPanel stats={stats} />
      </RightPanel>
    </>
  );
}
