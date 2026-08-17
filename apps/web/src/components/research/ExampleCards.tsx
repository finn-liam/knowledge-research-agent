import { Cpu, Dna, Globe2, Leaf, ShieldCheck, TrendingUp, type LucideIcon } from "lucide-react";

const EXAMPLES: { icon: LucideIcon; text: string }[] = [
  { icon: TrendingUp, text: "分析大语言模型技术未来发展趋势" },
  { icon: Cpu, text: "研究 AI 在金融行业的应用现状与未来" },
  { icon: ShieldCheck, text: "评估多模态大模型的技术突破方向" },
  { icon: Globe2, text: "分析全球自动驾驶技术竞争格局" },
  { icon: Dna, text: "研究生物医药领域 AI 技术应用趋势" },
  { icon: Leaf, text: "探索可持续能源技术未来发展路径" },
];

/** 首页「Try these examples」示例问题卡片组 */
export function ExampleCards({ onPick }: { onPick: (query: string) => void }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {EXAMPLES.map(({ icon: Icon, text }) => (
        <button
          key={text}
          onClick={() => onPick(text)}
          className="flex items-start gap-3 rounded-xl border bg-card p-3.5 text-left transition-all hover:border-primary/50 hover:shadow-md"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent">
            <Icon className="h-4 w-4 text-primary" />
          </div>
          <div className="text-[13px] font-medium leading-snug text-foreground/85">{text}</div>
        </button>
      ))}
    </div>
  );
}
