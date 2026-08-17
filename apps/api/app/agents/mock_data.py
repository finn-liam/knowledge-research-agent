"""Mock 数据层：无 Key / 外部服务不可用时，保证演示链路完整还原效果图2。

主题提取 + 模拟来源 + 模板化报告（含 [n] 引用）。
"""
import re

FALLBACK_TOPIC = "AI Agent 技术"

CHAT_KEYWORDS = [
    "你好", "您好", "在吗", "hi", "hello", "谢谢", "再见", "你是谁",
    "早上好", "中午好", "晚上好", "哈喽", "嗨", "辛苦", "感谢",
]


def mock_route(query: str) -> dict:
    """意图判断兜底（无 Key/LLM 失败）：问候词表启发式；极短输入视为闲聊。"""
    q = query.strip().lower()
    if any(k in q for k in CHAT_KEYWORDS) or len(q) <= 2:
        return {"type": "chat"}
    return {"type": "knowledge"}


def mock_query_process(query: str) -> dict:
    """查询增强兜底（无 Key/LLM 失败）：返回原问题，行为与现状一致。"""
    return {"rewritten_query": query, "keywords": []}

_STRIP_TOKENS = [
    "请", "帮我", "帮忙", "分析", "研究", "评估", "探索", "解读", "一下",
    "某技术方向", "未来发展趋势", "未来趋势", "发展趋势", "发展趋势与机遇",
    "趋势", "现状与未来", "现状", "未来", "。", "？", "?", "！", "!", "，", ",", " ",
]


def extract_topic(query: str) -> str:
    """从自然语言查询中提炼研究主题；过短时回退到演示主题（对齐效果图2）。"""
    topic = query.strip()
    for token in _STRIP_TOKENS:
        topic = topic.replace(token, "")
    topic = topic.strip()
    return topic if len(topic) >= 2 else FALLBACK_TOPIC


def is_agent_topic(topic: str) -> bool:
    lowered = topic.lower()
    return "agent" in lowered or "智能体" in topic


# ---------------- 规划 ----------------

def mock_plan(topic: str) -> dict:
    if is_agent_topic(topic):
        english_query = "AI agents large language model autonomous planning"
    else:
        english_query = f"{topic} technology trends"
    return {
        "topic": topic,
        "sub_queries": [
            f"{topic} 核心技术 最新进展",
            f"{topic} 行业应用 典型案例",
            f"{topic} 关键挑战 风险 发展路径",
        ],
        "english_query": english_query,
    }


# ---------------- 知识图谱子节点 ----------------

def mock_graph_children(topic: str) -> list[str]:
    if is_agent_topic(topic):
        return ["大语言模型", "强化学习", "多模态交互", "工程化工具", "自主规划", "应用场景"]
    return ["核心技术", "产业应用", "关键挑战", "生态工具", "标准规范", "演进方向"]


# ---------------- 模拟来源 ----------------

def mock_enterprise_sources(topic: str) -> list[dict]:
    return [
        {
            "title": f"{topic}内部技术文档",
            "url": "kb://internal/tech-doc",
            "snippet": f"企业内部沉淀的{topic}技术选型、架构设计与实践总结，覆盖核心链路的落地经验。",
            "type": "enterprise",
            "source_label": "企业知识库",
            "relevance": 0.95,
            "meta": {"simulated": True},
        },
        {
            "title": f"{topic}内部研究报告",
            "url": "kb://internal/research-report",
            "snippet": f"企业研究院出品的{topic}年度调研报告，包含竞品分析与技术雷达评估。",
            "type": "enterprise",
            "source_label": "企业知识库",
            "relevance": 0.94,
            "meta": {"simulated": True},
        },
    ]


def mock_paper_sources(topic: str) -> list[dict]:
    t = topic if not is_agent_topic(topic) else "AI Agent"
    return [
        {
            "title": f"arXiv:2401.12345 {t}: A Comprehensive Survey",
            "url": "https://arxiv.org/abs/2401.12345",
            "snippet": f"A comprehensive survey of {t}, covering architecture, planning, memory and tool-use capabilities.",
            "type": "paper",
            "source_label": "学术论文",
            "relevance": 0.92,
            "meta": {"simulated": True},
        },
        {
            "title": f"{t} Survey 2024: Advances and Open Challenges",
            "url": "https://arxiv.org/abs/2402.00001",
            "snippet": f"Recent advances of {t} in 2024 with analysis of open challenges and future directions.",
            "type": "paper",
            "source_label": "学术论文",
            "relevance": 0.89,
            "meta": {"simulated": True},
        },
    ]


def mock_web_sources(topic: str) -> list[dict]:
    return [
        {
            "title": f"{topic}最新进展全景解读 - InfoQ",
            "url": "https://www.infoq.cn/",
            "snippet": f"从产业视角梳理{topic}的最新进展、代表厂商与落地案例。",
            "type": "web",
            "source_label": "网页",
            "relevance": 0.87,
            "meta": {"simulated": True},
        },
        {
            "title": f"Hugging Face Blog: {topic} in Practice",
            "url": "https://huggingface.co/blog",
            "snippet": f"Engineering practice and open-source ecosystem around {topic}.",
            "type": "web",
            "source_label": "网页",
            "relevance": 0.87,
            "meta": {"simulated": True},
        },
        {
            "title": f"{topic}工程化实践指南 - 掘金",
            "url": "https://juejin.cn/",
            "snippet": f"一线工程师总结的{topic}工程化落地路径与踩坑记录。",
            "type": "web",
            "source_label": "网页",
            "relevance": 0.84,
            "meta": {"simulated": True},
        },
        {
            "title": f"{topic}行业应用观察 - 36氪",
            "url": "https://36kr.com/",
            "snippet": f"{topic}在金融、医疗、制造等行业的商业化进展与投融资动态。",
            "type": "web",
            "source_label": "网页",
            "relevance": 0.82,
            "meta": {"simulated": True},
        },
        {
            "title": f"{topic}技术趋势年度报告 - 艾瑞咨询",
            "url": "https://www.iresearch.com.cn/",
            "snippet": f"第三方咨询机构发布的{topic}技术趋势与市场规模预测。",
            "type": "web",
            "source_label": "网页",
            "relevance": 0.80,
            "meta": {"simulated": True},
        },
    ]


# ---------------- 模板化报告 ----------------

def _cite(nums: list[int], total: int) -> str:
    return "".join(f"[{n}]" for n in nums if 1 <= n <= total)


def build_mock_report(topic: str, sources: list[dict]) -> str:
    total = len(sources)
    if is_agent_topic(topic):
        trends = [
            ("自主性与智能化提升",
             f"未来 {topic} 将具备更强的自主决策能力，能够在复杂环境中独立完成多步骤任务。通过强化学习、大模型和工具使用能力的结合，Agent 将展现出更接近人类的智能水平。",
             [1, 2, 3]),
            ("多模态理解与交互",
             "多模态能力将成为 AI Agent 的标配，支持文本、图像、音频、视频等多种模态的理解和生成，提供更自然的交互体验。",
             [4, 5]),
            ("协作与群体智能",
             "多个 AI Agent 的协作将成为趋势，通过分布式任务分解和协同执行，解决更复杂的问题，群体智能将催生新的应用形态。",
             [6, 7]),
            ("行业应用深度化",
             "AI Agent 将在更多垂直行业实现深度应用，如金融、医疗、教育、制造等，创造显著的业务价值。",
             [8, 9]),
        ]
        drivers = [
            ("大语言模型的持续进步", "更强推理与规划能力为 Agent 提供认知底座。", [1]),
            ("强化学习与自我改进", "在线学习与反思机制逐步成熟，任务成功率持续提升。", [2]),
            ("工具生态完善", "函数调用、MCP 等协议大幅降低工具集成门槛。", [5]),
            ("算力与推理成本下降", "模型推理成本持续优化，推动 Agent 规模化落地。", [8]),
        ]
        risks = [
            ("可靠性不足", "长链路任务的错误累积仍需系统性解决，人机协同是过渡期常态。", [6]),
            ("安全与对齐", "自主决策带来的越权与失控风险需要完善治理框架。", [7]),
            ("评估体系缺失", "缺少公认的行业基准与度量标准，效果评估依赖场景化验证。", [9]),
        ]
        summary_core = ("AI Agent 技术正处于快速发展阶段，未来将在自主性、泛化能力、协作能力和"
                        "行业应用深度等方面取得突破性进展。本报告基于企业知识库、学术论文和网络信息"
                        "的综合分析，识别了关键趋势和发展机遇。")
        advice = ("建议企业从单点场景切入，优先落地人机协同的半自主 Agent，同步建设知识底座与评测体系，"
                  "逐步向多 Agent 协作演进，把握 2-3 年的技术窗口期。")
        advice_cites = [1, 4, 8]
    else:
        trends = [
            ("核心技术持续突破",
             f"{topic}的核心技术正加速迭代，性能指标与成本曲线持续优化，头部团队与开源社区形成双轮驱动。",
             [1, 2, 3]),
            ("多学科交叉融合",
             f"{topic}与人工智能、大数据、云计算等技术的交叉融合不断深化，催生出新的技术范式与产品形态。",
             [4, 5]),
            ("工程化与生态成熟",
             f"{topic}的工具链、平台化能力与标准规范逐步完善，工程化门槛显著降低，生态进入收获期。",
             [6, 7]),
            ("行业应用深度化",
             f"{topic}将在更多垂直行业实现深度应用，从试点示范走向规模化复制，创造显著的业务价值。",
             [8, 9]),
        ]
        drivers = [
            ("基础研究与论文产出", "学术界持续产出高质量成果，为产业落地提供源头供给。", [1]),
            ("开源生态繁荣", "开源项目降低企业采用门槛，加速技术扩散。", [5]),
            ("政策与资本加持", "产业政策与资本市场共同推动投入强度提升。", [8]),
            ("人才与工程积累", "工程人才密度提升，最佳实践快速沉淀。", [6]),
        ]
        risks = [
            ("技术成熟度不均", "部分方向仍处早期，需警惕过度预期带来的投资风险。", [6]),
            ("标准与合规不确定", "行业标准与监管框架尚在演进，合规成本需提前评估。", [7]),
            ("同质化竞争", "热门赛道拥挤，差异化定位与场景深耕成为关键。", [9]),
        ]
        summary_core = (f"{topic}正处于快速发展阶段，技术突破、生态成熟与行业需求形成共振。"
                        f"本报告基于企业知识库、学术论文和网络信息的综合分析，"
                        f"识别了{topic}的关键趋势和发展机遇。")
        advice = (f"建议企业围绕{topic}建立技术雷达机制，优先在高价值场景开展试点，"
                  f"同步储备核心人才与数据资产，分阶段推进规模化落地。")
        advice_cites = [1, 4, 8]

    lines: list[str] = [f"# {topic}未来趋势分析报告", ""]
    lines += ["## 一、执行摘要", ""]
    lines.append(f"{summary_core}{_cite([1, 2], total)}")
    lines.append("")
    lines += ["## 二、技术发展趋势", ""]
    for idx, (name, desc, cites) in enumerate(trends, start=1):
        lines.append(f"### {idx}. {name}")
        lines.append("")
        lines.append(f"{desc}{_cite(cites, total)}")
        lines.append("")
    lines += ["## 三、关键技术驱动因素", ""]
    for name, desc, cites in drivers:
        lines.append(f"- **{name}**：{desc}{_cite(cites, total)}")
    lines.append("")
    lines += ["## 四、挑战与风险", ""]
    for name, desc, cites in risks:
        lines.append(f"- **{name}**：{desc}{_cite(cites, total)}")
    lines.append("")
    lines += ["## 五、发展建议", ""]
    lines.append(f"{advice}{_cite(advice_cites, total)}")
    lines.append("")
    return "\n".join(lines)


def report_title(topic: str) -> str:
    return f"{topic}未来趋势分析报告"


def task_title(topic: str) -> str:
    return f"{topic}知识库问答"
