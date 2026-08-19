"""LangGraph 装配（意图路由 + 渐进式多源检索 + Self-RAG）：

START → router ──chat──→ report_write → END
             └─knowledge→ kb_search（先只查企业知识库）
                 kb_search ──有命中──→ merger（跳过论文/网页，省下游成本）
                 kb_search ──无命中──→ fanout → (paper_search ∥ web_search) → merger
                 （渐进式升级：KB 是默认路径，外部源按需补跑）
                 merger → grade
                 grade ──高相关──→ report_write → END
                 grade ──低分(<2次)──→ rewrite → 回到 kb_search（重检索）
                 grade ──耗尽──→ report_write（"未找到足够相关信息"分支）

知识图谱构建保持暂停（节点不在图中）。
"""
from langgraph.graph import END, START, StateGraph

from app.agents import nodes
from app.agents.state import ResearchState


def route_after_router(state: ResearchState):
    # 返回 path_map 的 key（chat/knowledge），而非目标节点名
    if state.get("query_type") == "chat":
        return "chat"
    return "knowledge"


def route_after_kb(state: ResearchState) -> str:
    """渐进式检索：KB 有命中 → 直接融合；无命中 → 升级补跑论文/网页。"""
    if state.get("kb_results"):
        return "hit"
    return "miss"


def route_after_grade(state: ResearchState) -> str:
    return state.get("route", "report")


def build_graph():
    g = StateGraph(ResearchState)

    g.add_node("router", nodes.router_node)
    g.add_node("kb_search", nodes.kb_retriever_node)
    g.add_node("fanout", nodes.fanout_node)
    g.add_node("paper_search", nodes.paper_retriever_node)
    g.add_node("web_search", nodes.web_retriever_node)
    g.add_node("merger", nodes.merger_node)
    g.add_node("grade", nodes.grade_documents_node)
    g.add_node("rewrite", nodes.rewrite_node)
    g.add_node("report_write", nodes.report_writer_node)

    # 意图路由：chat 直接生成回复；knowledge 先只查企业知识库
    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router",
        route_after_router,
        {
            "chat": "report_write",
            "knowledge": "kb_search",
        },
    )

    # 渐进式检索：KB 命中 → merger；KB 无命中 → fanout 升级补跑论文/网页
    g.add_conditional_edges(
        "kb_search",
        route_after_kb,
        {
            "hit": "merger",
            "miss": "fanout",
        },
    )
    g.add_edge("fanout", "paper_search")
    g.add_edge("fanout", "web_search")

    # 三路扇入融合（KB 命中时仅 kb_search 一路汇入）
    g.add_edge("paper_search", "merger")
    g.add_edge("web_search", "merger")

    # Self-RAG：grader 判断
    g.add_edge("merger", "grade")
    g.add_conditional_edges(
        "grade",
        route_after_grade,
        {
            "report": "report_write",
            "rewrite": "rewrite",
            "done": "report_write",
        },
    )
    # 重检索：改写后同样先查 KB（命中即融合，未命中再升级）
    g.add_edge("rewrite", "kb_search")

    g.add_edge("report_write", END)

    return g.compile()


_research_graph = None


def get_research_graph():
    global _research_graph
    if _research_graph is None:
        _research_graph = build_graph()
    return _research_graph
