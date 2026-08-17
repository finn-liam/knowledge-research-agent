"""LangGraph 装配（多源检索 + Self-RAG）：

START → (kb_search ∥ paper_search ∥ web_search) → merger → grade
   grade ──高相关──→ report_write → END
   grade ──低分(<2次)──→ rewrite → 回到三路并行（重检索）
   grade ──耗尽──→ report_write（"未找到足够相关信息"分支）

知识图谱构建保持暂停（节点不在图中）。
"""
from langgraph.graph import END, START, StateGraph

from app.agents import nodes
from app.agents.state import ResearchState


def route_after_grade(state: ResearchState) -> str:
    return state.get("route", "report")


def build_graph():
    g = StateGraph(ResearchState)

    g.add_node("kb_search", nodes.kb_retriever_node)
    g.add_node("paper_search", nodes.paper_retriever_node)
    g.add_node("web_search", nodes.web_retriever_node)
    g.add_node("merger", nodes.merger_node)
    g.add_node("grade", nodes.grade_documents_node)
    g.add_node("rewrite", nodes.rewrite_node)
    g.add_node("report_write", nodes.report_writer_node)

    # 三路并行扇出
    g.add_edge(START, "kb_search")
    g.add_edge(START, "paper_search")
    g.add_edge(START, "web_search")
    # 扇入融合
    g.add_edge("kb_search", "merger")
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
    # 重检索：改写后回到三路并行（重跑时 kb/paper/web 均用新查询）
    g.add_edge("rewrite", "kb_search")
    g.add_edge("rewrite", "paper_search")
    g.add_edge("rewrite", "web_search")

    g.add_edge("report_write", END)

    return g.compile()


_research_graph = None


def get_research_graph():
    global _research_graph
    if _research_graph is None:
        _research_graph = build_graph()
    return _research_graph
