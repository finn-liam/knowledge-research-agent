/**
 * 渲染级回归测试：验证 markdown 报告中的 [n] 引用被渲染为可点击徽标（data-report-ref）。
 *
 * 背景：react-markdown v10 移除了 components.text 特殊组件（实测调用 0 次），
 * 若未来有人再次改用 text 组件，本脚本将失败（防止静默回归）。
 *
 * 运行：node scripts/verify-citations.cjs
 */
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const ReactMarkdown = require("react-markdown").default || require("react-markdown");

function renderWithCitations(children) {
  return React.Children.map(children, (child) => {
    if (typeof child === "string") {
      const parts = child.split(/(\[\d+\])/g);
      if (parts.length === 1) return child;
      return parts.map((part, i) => {
        const match = /^\[(\d+)\]$/.exec(part);
        return match
          ? React.createElement("button", { key: i, "data-report-ref": match[1] }, `[${match[1]}]`)
          : part;
      });
    }
    if (React.isValidElement(child)) {
      const el = child;
      // 跳过已注入的引用徽标（防二次递归嵌套）
      if (el.props && el.props["data-report-ref"] != null) return child;
      if (el.props && el.props.children != null) {
        return React.cloneElement(el, undefined, renderWithCitations(el.props.children));
      }
    }
    return child;
  });
}

const components = {
  p: ({ children }) => React.createElement("p", null, renderWithCitations(children)),
  strong: ({ children }) => React.createElement("strong", null, renderWithCitations(children)),
  h2: ({ children }) => React.createElement("h2", null, renderWithCitations(children)),
};

const cases = [
  ["正文引用", "企业知识管理的 RAG 架构 [1]。切片策略 [2][3]。", 3],
  ["粗体内引用", "**关键结论 [1]** 与补充 [2]。", 2],
  ["标题内引用", "## 一、执行摘要 [1][2]", 2],
];

let pass = true;
for (const [name, md, expected] of cases) {
  const html = renderToStaticMarkup(
    React.createElement(ReactMarkdown, { components }, md),
  );
  const count = (html.match(/data-report-ref=/g) || []).length;
  const ok = count === expected;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}: 期望 ${expected} 个徽标, 实际 ${count}`);
  if (!ok) {
    console.log("  渲染输出:", html.slice(0, 200));
    pass = false;
  }
}

console.log(pass ? "CITATION_RENDER_PASS" : "CITATION_RENDER_FAIL");
process.exit(pass ? 0 : 1);
