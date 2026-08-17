import {
  Children,
  cloneElement,
  isValidElement,
  useEffect,
  type ReactElement,
  type ReactNode,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useResearchStore } from "@/features/research/researchStore";
import { CitationBadge } from "./CitationBadge";

/**
 * 文本节点递归处理：将 [n] 替换为可点击的 CitationBadge。
 * 注意：react-markdown v10 已移除 components.text 特殊组件（实测调用 0 次），
 * 因此必须在块级组件（p/li/strong/em/blockquote/标题）内递归处理 children。
 */
function renderWithCitations(children: ReactNode): ReactNode {
  return Children.map(children, (child) => {
    if (typeof child === "string") {
      const parts = child.split(/(\[\d+\])/g);
      if (parts.length === 1) return child;
      return parts.map((part, i) => {
        const match = /^\[(\d+)\]$/.exec(part);
        return match ? <CitationBadge key={i} n={parseInt(match[1], 10)} /> : part;
      });
    }
    if (isValidElement(child)) {
      const element = child as ReactElement<{ children?: ReactNode }>;
      // 跳过已注入的引用徽标，防止嵌套元素被二次递归导致徽标嵌套
      if (element.type === CitationBadge) return child;
      if (element.props.children != null) {
        return cloneElement(element, undefined, renderWithCitations(element.props.children));
      }
    }
    return child;
  });
}

const citationComponents = {
  p: ({ children }: { children?: ReactNode }) => <p>{renderWithCitations(children)}</p>,
  li: ({ children }: { children?: ReactNode }) => <li>{renderWithCitations(children)}</li>,
  strong: ({ children }: { children?: ReactNode }) => (
    <strong>{renderWithCitations(children)}</strong>
  ),
  em: ({ children }: { children?: ReactNode }) => <em>{renderWithCitations(children)}</em>,
  blockquote: ({ children }: { children?: ReactNode }) => (
    <blockquote>{renderWithCitations(children)}</blockquote>
  ),
  h1: ({ children }: { children?: ReactNode }) => <h1>{renderWithCitations(children)}</h1>,
  h2: ({ children }: { children?: ReactNode }) => <h2>{renderWithCitations(children)}</h2>,
  h3: ({ children }: { children?: ReactNode }) => <h3>{renderWithCitations(children)}</h3>,
  h4: ({ children }: { children?: ReactNode }) => <h4>{renderWithCitations(children)}</h4>,
};

/** Markdown 报告渲染器：注入可交互引用徽标，支持流式追加；点击右侧来源时反向滚动定位 [n] */
export function ReportViewer({ markdown, streaming }: { markdown: string; streaming: boolean }) {
  const selectedRefNo = useResearchStore((s) => s.selectedRefNo);

  // 反向联动：点击右侧来源 → 报告内对应 [n] 滚动定位（与来源区 data-ref-no 命名区分）
  useEffect(() => {
    if (selectedRefNo == null) return;
    requestAnimationFrame(() => {
      document
        .querySelector(`[data-report-ref="${selectedRefNo}"]`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }, [selectedRefNo]);

  if (!markdown) return null;
  return (
    <div className="report-body mt-5">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={citationComponents}>
        {markdown}
      </ReactMarkdown>
      {streaming && (
        <span className="ml-0.5 inline-block h-4 w-2 animate-pulse-soft rounded-sm bg-primary/70 align-text-bottom" />
      )}
    </div>
  );
}
