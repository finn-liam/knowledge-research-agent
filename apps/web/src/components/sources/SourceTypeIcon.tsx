import { Building2, FileText, Globe, GraduationCap, Newspaper, ScrollText } from "lucide-react";
import type { SourceType } from "@/types";
import { cn } from "@/lib/utils";

/** 来源类型 → 彩色图标（色彩语义对齐设计稿） */
const TYPE_STYLE: Record<SourceType, { icon: typeof Globe; fg: string; bg: string }> = {
  enterprise: { icon: Building2, fg: "text-blue-600", bg: "bg-blue-50" },
  paper: { icon: GraduationCap, fg: "text-violet-600", bg: "bg-violet-50" },
  web: { icon: Globe, fg: "text-cyan-600", bg: "bg-cyan-50" },
  news: { icon: Newspaper, fg: "text-orange-600", bg: "bg-orange-50" },
  patent: { icon: ScrollText, fg: "text-rose-600", bg: "bg-rose-50" },
  report: { icon: FileText, fg: "text-emerald-600", bg: "bg-emerald-50" },
};

export function SourceTypeIcon({ type, className }: { type: SourceType; className?: string }) {
  const style = TYPE_STYLE[type] ?? TYPE_STYLE.web;
  const Icon = style.icon;
  return (
    <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", style.bg, className)}>
      <Icon className={cn("h-4 w-4", style.fg)} />
    </div>
  );
}
