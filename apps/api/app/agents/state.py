"""LangGraph 研究状态定义。"""
import operator
from typing import Annotated, Any, TypedDict


def _merge_dict(a: dict | None, b: dict | None) -> dict:
    """并行节点并发写 metrics 时的合并器。"""
    return {**(a or {}), **(b or {})}


class ResearchState(TypedDict, total=False):
    task_id: str
    query: str                       # 当前活动查询（重检索改写后可能变化）
    original_query: str              # 用户原始问题（报告始终回答它）
    query_type: str                  # 意图路由结果：chat / knowledge
    topic: str                       # 从查询中提炼的研究主题
    lang: str                        # 报告语言偏好 zh / en
    mode: str
    plan: list[str]                  # Planner 产出的子查询
    kb_results: list[dict]
    paper_results: list[dict]
    web_results: list[dict]
    merged_sources: list[dict]       # 融合重排后、带 ref_no 与 relevance
    grade_results: list[dict]        # Retrieval Grader 打分结果
    retry_count: int                 # 重检索次数（上限 2）
    route: str                       # grade 后的路由：report / rewrite / done
    knowledge_graph: dict[str, Any]  # {"nodes": [...], "edges": [...]}
    report_md: str
    report_title: str
    citations: list[dict]
    metrics: Annotated[dict[str, Any], _merge_dict]
    errors: Annotated[list[str], operator.add]
