import { Providers } from "@/app/providers";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { TopNav } from "@/components/layout/TopNav";

/** 全局骨架：顶栏 + 左侧边栏 + 主内容（右侧面板由各页面自渲染） */
export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <div className="flex h-screen flex-col overflow-x-clip">
        <TopNav />
        <div className="flex min-h-0 flex-1">
          <AppSidebar />
          {children}
        </div>
      </div>
    </Providers>
  );
}
