import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  BookOpen,
  Database,
  FileSearch,
  Home,
  Layers,
  Plus,
  Settings,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { UserProfileCard } from "@/components/user/UserProfileCard";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUserStore } from "@/features/user/userStore";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Home", icon: Home },
  { to: "/library", label: "Library", icon: BookOpen },
  { to: "/knowledge-base", label: "Knowledge Base", icon: Database },
  { to: "/datasources", label: "Datasources", icon: Layers },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Settings },
];

/** 左侧边栏：New Research / 主导航 / Recent Research / Enterprise Plan */
export function AppSidebar() {
  const navigate = useNavigate();
  const recentLimit = useUserStore((s) => s.recentLimit);
  const { data: recent } = useQuery({
    queryKey: ["recent-research", recentLimit],
    queryFn: () => api.listResearch(recentLimit),
    refetchInterval: 15000,
  });

  return (
    <aside className="flex w-[232px] min-w-0 shrink-0 flex-col border-r bg-secondary/40">
      <div className="p-3">
        <Button
          variant="outline"
          className="w-full justify-start gap-2 bg-card font-medium"
          onClick={() => navigate("/")}
        >
          <Plus className="h-4 w-4" />
          New Research
        </Button>
      </div>

      <nav className="space-y-0.5 px-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-5 px-4 text-xs font-medium text-muted-foreground">Recent Research</div>
      <ScrollArea className="mt-1 flex-1 px-3">
        {recent && recent.length > 0 ? (
          <div className="space-y-0.5 pb-3">
            {recent.map((t) => (
              <button
                key={t.id}
                onClick={() => navigate(`/research/${t.id}`)}
                className="w-full rounded-lg px-3 py-2 text-left transition-colors hover:bg-accent/50"
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
