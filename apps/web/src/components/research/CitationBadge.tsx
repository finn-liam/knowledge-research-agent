import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useResearchStore } from "@/features/research/researchStore";
import { cn } from "@/lib/utils";

/** 报告内 [n] 引用徽标：悬停显示来源；点击联动右侧 Sources 面板；选中时高亮 */
export function CitationBadge({ n }: { n: number }) {
  const source = useResearchStore((s) => s.sources.find((x) => x.ref_no === n));
  const selectedRefNo = useResearchStore((s) => s.selectedRefNo);
  const selectSource = useResearchStore((s) => s.selectSource);
  const selected = selectedRefNo === n;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          data-report-ref={n}
          onClick={() => selectSource(selected ? null : n)}
          className={cn(
            "mx-px rounded px-0.5 text-[12px] font-semibold text-primary transition-colors hover:bg-accent",
            selected && "rounded bg-accent ring-1 ring-primary/40",
          )}
        >
          [{n}]
        </button>
      </TooltipTrigger>
      <TooltipContent>
        {source ? `${source.title} · ${source.source_label}` : `来源 [${n}]`}
      </TooltipContent>
    </Tooltip>
  );
}
