import type { StepInfo } from "@/types";
import { AgentStepCard } from "./AgentStepCard";

/** 5 张 Agent 步骤卡片横排（查询企业知识库/检索学术论文/搜索网页信息/建立知识关系图谱/生成分析报告） */
export function AgentStepCards({ steps }: { steps: StepInfo[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {steps.map((step) => (
        <AgentStepCard key={step.step_key} step={step} />
      ))}
    </div>
  );
}
