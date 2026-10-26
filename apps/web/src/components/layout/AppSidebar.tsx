"use client";

import { useQuery } from "@tanstack/react-query";
import { FileSearch, Plus } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { NAV_ITEMS } from "@/components/layout/nav";
import { UserProfileCard } from "@/components/user/UserProfileCard";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUserStore } from "@/features/user/userStore";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

/** 左侧边栏：New Research / 主导航 / Recent Research / 用户卡（<lg 隐藏，移动端由顶栏抽屉接管） */
export function AppSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const recentLimit = useUserStore((s) => s.recentLimit);
  const { data: recent } = useQuery({
    queryKey: ["recent-research", recentLimit],
    queryFn: () => api.listResearch(recentLimit),
    refetchInterval: 15000,
  });

  return (
    <aside className="hidden w-[232px] min-w-0 shrink-0 flex-col border-r bg-secondary/40 lg:flex">
      <div className="p-3">
        <Button
          variant="outline"
          className="w-full justify-start gap-2 bg-card font-medium"
          onClick={() => router.push("/")}
        >
          <Plus className="h-4 w-4" />
          New Research
        </Button>
      </div>

      <nav className="space-y-0.5 px-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
          const isActive = to === "/" ? pathname === "/" : pathname.startsWith(to);
          return (
            <Link
              key={to}
              href={to}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-300 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* px-6 与导航项文字左缘（12+12px）光学对齐 */}
      <div className="mt-5 px-6 text-xs font-medium text-muted-foreground">Recent Research</div>
      <ScrollArea className="mt-1 flex-1 px-3">
        {recent && recent.length > 0 ? (
          <div className="space-y-0.5 pb-3">
            {recent.map((t) => (
              <button
                key={t.id}
                onClick={() => router.push(`/research/${t.id}`)}
                title={t.title || t.query}
                className="w-full rounded-lg px-3 py-2 text-left transition-colors duration-300 hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <div className="truncate text-[13px] font-medium text-foreground/90">
                  {t.title || t.query}
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {relativeTime(t.created_at)}
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center px-4 pb-6 pt-10 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/60">
              <FileSearch className="h-7 w-7 text-primary/70" />
            </div>
            <div className="mt-3 text-[13px] font-medium text-foreground/80">
              No recent research yet
            </div>
            <div className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Your research history will appear here
            </div>
          </div>
        )}
      </ScrollArea>

      <div className="p-3">
        <UserProfileCard />
      </div>
    </aside>
  );
}
