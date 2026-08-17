/** 知识图谱空状态：虚线放射插画 + 提示文案（对齐效果图1） */
export function GraphEmptyState({ hint = "Your knowledge connections will appear here" }: { hint?: string }) {
  return (
    <div className="flex flex-col items-center py-6">
      <svg width="180" height="120" viewBox="0 0 180 120" className="text-primary/30">
        {Array.from({ length: 8 }).map((_, i) => {
          const angle = (i / 8) * Math.PI * 2;
          const x = 90 + Math.cos(angle) * 62;
          const y = 60 + Math.sin(angle) * 40;
          return (
            <g key={i}>
              <line x1="90" y1="60" x2={x} y2={y} stroke="currentColor" strokeDasharray="3 4" strokeWidth="1" />
              <circle cx={x} cy={y} r="5" className="fill-primary/15" />
            </g>
          );
        })}
        <circle cx="90" cy="60" r="12" className="fill-primary/25" />
      </svg>
      <div className="mt-3 max-w-[200px] text-center text-xs leading-relaxed text-muted-foreground">
        {hint}
      </div>
    </div>
  );
}
