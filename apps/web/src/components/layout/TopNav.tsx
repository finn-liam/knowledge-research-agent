"use client";

import { useQuery } from "@tanstack/react-query";
import { Menu, Plus } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useMounted } from "@/hooks/use-mounted";
import { useUserStore, userInitials } from "@/features/user/userStore";
import { NAV_ITEMS } from "@/components/layout/nav";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

/** 品牌标：iconfont「知识图谱」图标（作者 ID 9833319，单色 currentColor，随主题着色） */
function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 1024 1024" fill="currentColor" className={className} aria-hidden>
      <path d="M405.333333 341.333333a64 64 0 1 1-64 64 64 64 0 0 1 64-64m0-42.666666a106.666667 106.666667 0 1 0 106.666667 106.666666 106.666667 106.666667 0 0 0-106.666667-106.666666zM618.666667 554.666667a64 64 0 1 1-64 64 64 64 0 0 1 64-64m0-42.666667a106.666667 106.666667 0 1 0 106.666666 106.666667 106.666667 106.666667 0 0 0-106.666666-106.666667zM509.866667 384a106.666667 106.666667 0 0 1 0 42.666667H853.333333v426.666666H426.666667V509.866667a106.666667 106.666667 0 0 1-42.666667 0V896h512V384zM512 618.666667a116.693333 116.693333 0 0 1 2.133333-21.333334H170.666667V170.666667h426.666666v343.466666a107.733333 107.733333 0 0 1 42.666667 0V128H128v512h386.133333a116.693333 116.693333 0 0 1-2.133333-21.333333z" />
    </svg>
  );
}

/** 顶栏：品牌标 + 产品名 + 用户头像；<lg 追加菜单按钮打开导航抽屉（与侧边栏同源数据） */
export function TopNav() {
  const mounted = useMounted();
  const username = useUserStore((s) => s.username);
  const recentLimit = useUserStore((s) => s.recentLimit);
  const router = useRouter();
  const pathname = usePathname();
  const { data: recent } = useQuery({
    queryKey: ["recent-research", recentLimit],
    queryFn: () => api.listResearch(recentLimit),
    refetchInterval: 15000,
  });

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b bg-card px-4">
      <div className="flex items-center gap-2.5">
        {/* 移动端菜单：抽屉复用侧边栏的导航与最近研究（<lg 才显示） */}
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8 lg:hidden" aria-label="打开导航菜单">
              <Menu className="h-4.5 w-4.5" />
            </Button>
          </DialogTrigger>
          <DialogContent
            className="left-0 top-0 h-full max-w-[300px] translate-x-0 translate-y-0 rounded-none rounded-r-2xl border-r p-0 animate-slide-left"
            aria-describedby={undefined}
          >
            <DialogTitle className="sr-only">导航菜单</DialogTitle>
            <div className="flex h-full flex-col overflow-y-auto p-3">
              <Button
                variant="outline"
                className="w-full justify-start gap-2 bg-card font-medium"
                onClick={() => router.push("/")}
              >
                <Plus className="h-4 w-4" />
                New Research
              </Button>

              <nav className="mt-3 space-y-0.5">
                {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
                  const isActive = to === "/" ? pathname === "/" : pathname.startsWith(to);
                  return (
                    <DialogClose asChild key={to}>
                      <Link
                        href={to}
                        className={cn(
                          "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-300",
                          isActive
                            ? "bg-accent text-accent-foreground"
                            : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                        )}
                      >
                        <Icon className="h-4 w-4" />
                        {label}
                      </Link>
                    </DialogClose>
                  );
                })}
              </nav>

              {recent && recent.length > 0 && (
                <>
                  <div className="mt-5 px-3 text-xs font-medium text-muted-foreground">
                    Recent Research
                  </div>
                  <div className="mt-1 space-y-0.5 pb-3">
                    {recent.map((t) => (
                      <DialogClose asChild key={t.id}>
                        <button
                          onClick={() => router.push(`/research/${t.id}`)}
                          title={t.title || t.query}
                          className="w-full rounded-lg px-3 py-2 text-left transition-colors duration-300 hover:bg-accent/50"
                        >
                          <div className="truncate text-[13px] font-medium text-foreground/90">
                            {t.title || t.query}
                          </div>
                          <div className="mt-0.5 text-xs text-muted-foreground">
                            {relativeTime(t.created_at)}
                          </div>
                        </button>
                      </DialogClose>
                    ))}
                  </div>
                </>
              )}
            </div>
          </DialogContent>
        </Dialog>
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <BrandMark className="h-[18px] w-[18px]" />
        </div>
        <span className="text-[15px] font-semibold text-foreground">
          Knowledge Research Agent
        </span>
      </div>

      <Avatar className="h-8 w-8">
        <AvatarFallback>{userInitials(mounted ? username : "")}</AvatarFallback>
      </Avatar>
    </header>
  );
}
