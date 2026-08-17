import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";

const STATUS_LABEL: Record<string, { text: string; variant: "default" | "secondary" | "destructive" }> = {
  done: { text: "已完成", variant: "secondary" },
  running: { text: "进行中", variant: "default" },
  failed: { text: "失败", variant: "destructive" },
};

/** Library：历史研究报告列表 */
export function LibraryPage() {
  const navigate = useNavigate();
  const { data: tasks } = useQuery({
    queryKey: ["library"],
    queryFn: () => api.listResearch(50),
    refetchInterval: 10000,
  });

  return (
    <ScrollArea className="min-w-0 flex-1">
      <div className="mx-auto max-w-[860px] px-8 py-8">
        <h1 className="text-xl font-bold">Library</h1>
        <p className="mt-1 text-sm text-muted-foreground">全部研究报告</p>
        <div className="mt-6 space-y-2.5">
          {(tasks ?? []).map((t) => {
            const status = STATUS_LABEL[t.status] ?? STATUS_LABEL.running;
            return (
              <Card
                key={t.id}
                className="cursor-pointer transition-all hover:border-primary/50 hover:shadow-md"
                onClick={() => navigate(`/research/${t.id}`)}
              >
                <CardContent className="flex items-center justify-between p-4">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{t.title || t.query}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {relativeTime(t.created_at)}
                    </div>
                  </div>
                  <Badge variant={status.variant}>{status.text}</Badge>
                </CardContent>
              </Card>
            );
          })}
          {tasks && tasks.length === 0 && (
            <div className="py-16 text-center text-sm text-muted-foreground">
              还没有研究报告，从首页发起你的第一个研究吧
            </div>
          )}
        </div>
      </div>
    </ScrollArea>
  );
}
