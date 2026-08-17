import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useUserStore } from "@/features/user/userStore";
import { AppSidebar } from "./AppSidebar";
import { TopNav } from "./TopNav";

/** 全局骨架：顶栏 + 左侧边栏 + 主内容（右侧面板由各页面自渲染） */
export function AppLayout() {
  const theme = useUserStore((s) => s.theme);

  // 深色主题：切换 <html> 的 dark class
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex h-screen flex-col overflow-hidden">
        <TopNav />
        <div className="flex min-h-0 flex-1">
          <AppSidebar />
          <Outlet />
        </div>
      </div>
    </TooltipProvider>
  );
}
