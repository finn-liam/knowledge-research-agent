import { Check, Languages, ListOrdered, Moon, Sun } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useUserStore, type ReportLang, type ThemeMode } from "@/features/user/userStore";
import { cn } from "@/lib/utils";

function OptionRow<T extends string | number>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string; icon?: typeof Sun }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div>
      <div className="mb-2 text-sm font-medium">{label}</div>
      <div className="flex gap-2">
        {options.map((opt) => {
          const active = opt.value === value;
          const Icon = opt.icon;
          return (
            <button
              key={String(opt.value)}
              onClick={() => onChange(opt.value)}
              className={cn(
                "flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition-all",
                active
                  ? "border-primary bg-accent font-medium text-accent-foreground"
                  : "text-muted-foreground hover:border-primary/40",
              )}
            >
              {Icon && <Icon className="h-4 w-4" />}
              {opt.label}
              {active && <Check className="h-3.5 w-3.5 text-primary" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** 个性化：主题（浅/深）+ 报告语言 + 历史条数，全部即时生效并持久化 */
export function PersonalizeDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const { theme, reportLang, recentLimit, setTheme, setReportLang, setRecentLimit } =
    useUserStore();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>个性化</DialogTitle>
          <DialogDescription>偏好即时生效，保存在本地浏览器</DialogDescription>
        </DialogHeader>
        <div className="space-y-5">
          <OptionRow<ThemeMode>
            label="界面主题"
            value={theme}
            onChange={setTheme}
            options={[
              { value: "light", label: "浅色", icon: Sun },
              { value: "dark", label: "深色", icon: Moon },
            ]}
          />
          <OptionRow<ReportLang>
            label="报告语言"
            value={reportLang}
            onChange={setReportLang}
            options={[
              { value: "zh", label: "中文", icon: Languages },
              { value: "en", label: "English", icon: Languages },
            ]}
          />
          <OptionRow<number>
            label="最近研究显示条数"
            value={recentLimit}
            onChange={setRecentLimit}
            options={[
              { value: 5, label: "5 条", icon: ListOrdered },
              { value: 8, label: "8 条", icon: ListOrdered },
              { value: 15, label: "15 条", icon: ListOrdered },
            ]}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
