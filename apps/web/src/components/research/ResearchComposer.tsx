"use client";

import { SendHorizontal } from "lucide-react";
import { useRef, useState } from "react";
import { useMagnetic } from "@/hooks/use-magnetic";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ResearchComposerProps {
  variant: "hero" | "followup";
  onSubmit: (query: string) => void;
  disabled?: boolean;
}

/** 研究输入框：hero=首页大号 / followup=研究页追问；高度随内容平滑生长 */
export function ResearchComposer({ variant, onSubmit, disabled }: ResearchComposerProps) {
  const [value, setValue] = useState("");
  const hero = variant === "hero";
  const sendRef = useMagnetic<HTMLButtonElement>();
  const taRef = useRef<HTMLTextAreaElement>(null);

  const autoResize = () => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  const submit = () => {
    const query = value.trim();
    if (!query || disabled) return;
    onSubmit(query);
    setValue("");
    if (taRef.current) taRef.current.style.height = "";
  };

  return (
    <div
      className={cn(
        "rounded-2xl border bg-card shadow-sm transition-colors focus-within:border-primary/60 focus-within:ring-1 focus-within:ring-primary/30",
        hero ? "border-primary/25" : "border-input",
      )}
    >
      <textarea
        ref={taRef}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          autoResize();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        rows={hero ? 3 : 1}
        placeholder={hero ? "Ask any research question..." : "Ask follow-up questions..."}
        className={cn(
          "w-full resize-none rounded-2xl bg-transparent px-4 pt-3.5 text-[15px] outline-none transition-[height] duration-200 ease-out placeholder:text-muted-foreground/80",
          hero ? "min-h-[72px]" : "min-h-[40px] pt-3",
        )}
      />
      <div className="flex items-center justify-between px-3 pb-3">
        {hero ? (
          <div className="pl-1 text-xs text-muted-foreground/70">
            Enter 发送 · Shift + Enter 换行
          </div>
        ) : (
          <span />
        )}
        <Button
          ref={sendRef}
          size="icon"
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label="提交研究问题"
          className="magnetic h-9 w-9 rounded-full"
        >
          <SendHorizontal className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
