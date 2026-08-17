import { Avatar, AvatarFallback } from "@/components/ui/avatar";

/** 用户提问气泡（对齐效果图2 的紫色头像 + 淡紫气泡） */
export function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex items-start gap-3">
      <Avatar className="h-8 w-8">
        <AvatarFallback>YC</AvatarFallback>
      </Avatar>
      <div className="rounded-xl rounded-tl-sm bg-accent/80 px-4 py-2.5 text-sm leading-relaxed text-foreground">
        {content}
      </div>
    </div>
  );
}
