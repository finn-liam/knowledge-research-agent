import { Plus, SendHorizontal } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ResearchComposerProps {
  variant: "hero" | "followup";
  onSubmit: (query: string) => void;
  disabled?: boolean;
}

/** 研究输入框：hero=首页大号 / followup=研究页追问（已移除 Deep Research 下拉） */
export function ResearchComposer({ variant, onSubmit, disabled }: ResearchComposerProps) {
  const [value, setValue] = useState("");
  const hero = variant === "hero";

  const submit = () => {
    const query = value.trim();
    if (!query || disabled) return;
    onSubmit(query);
    setValue("");
  };

  return (
    <div
      className={cn(
        "rounded-2xl border bg-card shadow-sm transition-colors focus-within:border-primary/60",
        hero ? "border-primary/25" : "border-input",
      )}
    >
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        rows={hero ? 3 : 1}
        placeholder={hero ? "Ask any research question..." : "Ask follow-up questions..."}
        className={cn(
          "w-full resize-none rounded-2xl bg-transparent px-4 pt-3.5 text-[15px] outline-none placeholder:text-muted-foreground/80",
          hero ? "min-h-[72px]" : "min-h-[40px] pt-3",
        )}
      />
      <div className="flex items-center justify-between px-3 pb-3">
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
          <Plus className="h-4.5 w-4.5" />
        </Button>
        <Button
          size="icon"
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="h-9 w-9 rounded-full"
        >
          <SendHorizontal className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
