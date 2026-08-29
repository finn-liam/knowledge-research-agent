"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useMounted } from "@/hooks/use-mounted";
import { useUserStore, userInitials } from "@/features/user/userStore";

/** 用户提问气泡（对齐效果图2 的紫色头像 + 淡紫气泡），头像缩写跟随个性化用户名 */
export function UserBubble({ content }: { content: string }) {
  const mounted = useMounted();
  const persistedName = useUserStore((s) => s.username);
  return (
    <div className="flex items-start gap-3">
      <Avatar className="h-8 w-8">
        <AvatarFallback>{userInitials(mounted ? persistedName : "")}</AvatarFallback>
      </Avatar>
      <div className="rounded-xl rounded-tl-sm bg-accent/80 px-4 py-2.5 text-sm leading-relaxed text-foreground">
        {content}
      </div>
    </div>
  );
}
