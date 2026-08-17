import { ChevronDown } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useUserStore, userInitials } from "@/features/user/userStore";

/** 顶栏：Logo + 产品名 + 用户头像（与用户卡片联动） */
export function TopNav() {
  const username = useUserStore((s) => s.username);
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b bg-card px-4">
      <div className="flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
          K
        </div>
        <button className="flex items-center gap-1 text-[15px] font-semibold text-foreground">
          Knowledge Research Agent
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </button>
      </div>
      <Avatar className="h-8 w-8">
        <AvatarFallback>{userInitials(username)}</AvatarFallback>
      </Avatar>
    </header>
  );
}
