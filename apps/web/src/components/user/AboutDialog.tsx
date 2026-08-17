import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

/** 关于：产品与技术信息 */
export function AboutDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
              K
            </span>
            Knowledge Research Agent
          </DialogTitle>
          <DialogDescription>企业级 AI Research Assistant</DialogDescription>
        </DialogHeader>
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">版本</span>
            <Badge variant="secondary">v0.1.0 (Phase 1)</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Agent 编排</span>
            <span>LangGraph · 7 节点状态机</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">LLM</span>
            <span>DeepSeek deepseek-v4-flash</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">向量 / 精排</span>
            <span>bge-m3 / bge-reranker-v2-m3</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">数据源</span>
            <span>企业知识库 · arXiv · Tavily</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
