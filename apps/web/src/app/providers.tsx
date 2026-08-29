"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useUserStore } from "@/features/user/userStore";

/** 深色主题：同步 <html> 的 dark class（原 AppLayout 职责） */
function ThemeSync() {
  const theme = useUserStore((s) => s.theme);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  // SSR 阶段不发请求（fetch 相对路径在 Node 侧无效），客户端挂载后正常查询
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false,
            staleTime: 30_000,
            enabled: typeof window !== "undefined",
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={200}>
        <ThemeSync />
        {children}
      </TooltipProvider>
    </QueryClientProvider>
  );
}
