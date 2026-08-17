"""语义切片：按段落聚合至目标 token 数，长段句子级硬切，跨块 100 token 重叠。

Parent-Child 结构：child=650 token 检索单元；parent=章节级上下文（≤2000 token）。
"""
import re

import tiktoken

TARGET_TOKENS = 650
MIN_TOKENS = 400
MAX_TOKENS = 900
OVERLAP_TOKENS = 100
PARENT_MAX_TOKENS = 2000

_tokenizer = tiktoken.get_encoding("cl100k_base")

TITLE_RE = re.compile(r"^#{1,4}\s+.*$", re.MULTILINE)
PAGE_RE = re.compile(r"\[第(\d+)页\]")


def chunk_page_nos(text: str) -> list[int]:
    """从 chunk 文本提取出现的页码（[第N页] 标记），返回升序去重列表。"""
    return sorted({int(m) for m in PAGE_RE.findall(text)})


def count_tokens(text: str) -> int:
    return len(_tokenizer.encode(text))


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？；!?;])", text)
    return [p.strip() for p in parts if p.strip()]


def _tail_overlap(text: str, tokens: int) -> str:
    """截取 text 末尾约 tokens 个 token 的文本作为重叠前缀。"""
    encoded = _tokenizer.encode(text)
    if len(encoded) <= tokens:
        return text
    return _tokenizer.decode(encoded[-tokens:])


def _chunk_section(text: str) -> list[str]:
    """章节内切片核心：段落聚合至目标 token，句级硬切，跨块重叠。"""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current, current_tokens
        if not current:
            return
        joined = "\n\n".join(current)
        # 超长块按句子硬切
        if count_tokens(joined) > MAX_TOKENS:
            for sentence in _split_sentences(joined):
                if sentence:
                    chunks.append(sentence)
        else:
            chunks.append(joined)
        current = []
        current_tokens = 0

    last_chunk_text = ""
    for para in paragraphs:
        para_tokens = count_tokens(para)
        if para_tokens > MAX_TOKENS:
            flush()
            for sentence in _split_sentences(para):
                if sentence:
                    chunks.append(sentence)
            continue

        if current and current_tokens + para_tokens > TARGET_TOKENS:
            flush()
            # 重叠：上一块尾部 100 token 前置于新块
            if last_chunk_text:
                overlap = _tail_overlap(last_chunk_text, OVERLAP_TOKENS)
                current.append(overlap)
                current_tokens = count_tokens(overlap)

        current.append(para)
        current_tokens += para_tokens

    flush()
    if chunks:
        last_chunk_text = chunks[-1]

    # 过滤过短噪声块（< 10 token 且仅一个）
    return [c for c in chunks if count_tokens(c) >= 8] or chunks


def chunk_text(text: str) -> list[str]:
    """兼容旧接口：扁平切片（无层级）。"""
    return _chunk_section(text)


def _split_sections(text: str) -> list[tuple[str, str]]:
    """按 Markdown 标题（#~####）拆章：返回 [(标题行, 章节正文)]。"""
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_body: list[str] = []
    for line in text.split("\n"):
        if TITLE_RE.match(line.strip()):
            if current_title or any(l.strip() for l in current_body):
                sections.append((current_title, "\n".join(current_body)))
            current_title = line.strip()
            current_body = []
        else:
            current_body.append(line)
    if current_title or any(l.strip() for l in current_body):
        sections.append((current_title, "\n".join(current_body)))
    return sections


def _truncate_tokens(text: str, max_tokens: int) -> str:
    encoded = _tokenizer.encode(text)
    if len(encoded) <= max_tokens:
        return text
    return _tokenizer.decode(encoded[:max_tokens])


def chunk_text_hierarchical(text: str) -> list[dict]:
    """Parent-Child 切片：返回 [{parent, child}]。

    child 为 650 token 检索单元；parent 为章节级上下文（≤2000 token）。
    无标题文档 → 整个文档作为单一 parent。
    """
    sections = _split_sections(text)
    if not sections:
        sections = [("", text)]
    result: list[dict] = []
    for title, body in sections:
        childs = _chunk_section(body)
        if not childs:
            continue
        parent = _truncate_tokens((f"{title}\n{body}" if title else body), PARENT_MAX_TOKENS)
        for child in childs:
            result.append({"parent": parent, "child": child})
    return result
