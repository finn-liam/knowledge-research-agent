import { useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { GraphMiniPanel } from "@/components/graph/GraphMiniPanel";
import { RightPanel } from "@/components/layout/RightPanel";
import { AgentHeader } from "@/components/research/AgentHeader";
import { AgentStepCards } from "@/components/research/AgentStepCards";
import { Disclaimer } from "@/components/research/Disclaimer";
import { ReportHeader } from "@/components/research/ReportHeader";
import { ReportViewer } from "@/components/research/ReportViewer";
import { ResearchComposer } from "@/components/research/ResearchComposer";
import { UserBubble } from "@/components/research/UserBubble";
import { SourcesPanel } from "@/components/sources/SourcesPanel";
import { RunStatsPanel } from "@/components/stats/RunStatsPanel";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useResearchStore } from "@/features/research/researchStore";
import { useResearchStream } from "@/features/research/useResearchStream";
import { useUserStore } from "@/features/user/userStore";
import { api } from "@/lib/api";

/** 研究报告页：多轮对话流 + 当前轮步骤卡 + 流式报告 + 右侧面板（对齐效果图2） */
export function ResearchPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const store = useResearchStore();

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
    await api.followup(taskId, query, lang);
    useResearchStore.getState().beginRun(taskId, query, useResearchStore.getState().title);
  };

  const lastMsgIndex = Math.max(0, store.messages.length - 1);
  // 当前轮报告：流式中只用本轮 buffer（空 → 骨架屏，绝不回退上一轮报告）；
  // 仅完成后 buffer 为空（如重连快照未恢复）才回退 reports 最后一项
  const currentReport =
    store.phase === "streaming"
      ? store.reportBuffer
      : store.reportBuffer || store.reports.at(-1)?.markdown || "";
  const streaming = store.phase === "streaming";

  // 流式输出期间自动滚动到底部（让用户始终看到最新生成的回答）
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (streaming && store.reportBuffer) {
      bottomRef.current?.scrollIntoView({ behavior: "auto", block: "end", inline: "nearest" });
      if (window.scrollX !== 0) window.scrollTo({ left: 0 });
    }
  }, [store.reportBuffer, streaming]);

  return (
    <>
      <div className="flex min-w-0 flex-1 flex-col">
        <ReportHeader
          title={store.reportTitle || store.title}
          taskId={taskId ?? null}
          canExport={store.phase === "done"}
        />

        <ScrollArea className="min-h-0 flex-1">
          <div className="mx-auto max-w-[860px] space-y-5 px-8 py-6">
            {/* 多轮对话：每轮 = 用户气泡 + Agent 报告块 */}
            {store.messages.map((msg, i) => {
              const isLast = i === lastMsgIndex;
              const report = i < store.reports.length ? store.reports[i].markdown : null;
              return (
                <div key={i} className="space-y-4">
                  <UserBubble content={msg.content} />
                  {isLast ? (
                    <div className="space-y-4">
                      <AgentHeader phase={store.phase} />
                      <AgentStepCards steps={store.steps} />

                      {store.phase === "failed" && (
                        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
                          研究过程出现错误：{store.error ?? "未知错误"}，请重试。
                        </div>
                      )}

                      {store.phase === "interrupted" && (
                        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                          连接中断，研究可能未完成。请刷新页面查看最终结果，或重新提问。
                        </div>
                      )}

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
            {/* 流式自动滚动定位锚点 */}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        <div className="border-t bg-background px-8 pb-2 pt-3">
          <div className="mx-auto max-w-[860px]">
            <ResearchComposer
              variant="followup"
              onSubmit={followup}
              disabled={store.phase === "streaming"}
            />
            <Disclaimer />
          </div>
        </div>
      </div>

      <RightPanel>
        <SourcesPanel sources={store.sources} />
        <GraphMiniPanel graph={store.graph} hint="知识图谱功能暂缓，将在后续版本启用" />
        <RunStatsPanel stats={store.stats} />
      </RightPanel>
    </>
  );
}
