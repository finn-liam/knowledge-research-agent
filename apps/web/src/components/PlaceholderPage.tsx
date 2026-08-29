import { Hammer, type LucideIcon } from "lucide-react";

/** 占位页（Phase 3 建设内容）：Knowledge Base / Datasources / Analytics / Settings */
export function PlaceholderPage({ title, icon: Icon = Hammer }: { title: string; icon?: LucideIcon }) {
  return (
    <div className="flex min-w-0 flex-1 flex-col items-center justify-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-accent/60">
        <Icon className="h-8 w-8 text-primary/70" />
      </div>
      <h1 className="mt-4 text-lg font-semibold">{title}</h1>
      <p className="mt-1.5 text-sm text-muted-foreground">该模块将在 Phase 3 提供，敬请期待</p>
    </div>
  );
}
