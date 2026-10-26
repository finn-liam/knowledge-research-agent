"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useMounted } from "@/hooks/use-mounted";
import { useUserStore, userInitials } from "@/features/user/userStore";

/** 用户提问：与 AI 输出同款裸文本样式（无底色无边框），仅以右对齐 + 右侧头像区分角色 */
export function UserBubble({ content }: { content: string }) {
  const mounted = useMounted();
  const persistedName = useUserStore((s) => s.username);
  return (
    <div className="anim-in-right flex items-start justify-end gap-3">
      <div className="max-w-[85%] py-0.5 text-[15px] leading-relaxed text-foreground">
        {content}
      </div>
      <Avatar className="h-8 w-8">
        <AvatarFallback>{userInitials(mounted ? persistedName : "")}</AvatarFallback>
      </Avatar>
    </div>
  );
}
