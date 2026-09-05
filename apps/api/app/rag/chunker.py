"""语义切片：按段落聚合至目标 token 数，长段句子级硬切，跨块 100 token 重叠。

Parent-Child 结构：child=650 token 检索单元；parent=章节级上下文（≤2000 token）。
代码块感知：围栏代码块（```）保持原子性——不与散文聚合、不按句子切分
（代码的 `;` 不是句子边界），超长按行硬切，并前置最近散文行作为检索语义锚。
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
CODE_FENCE = "```"


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


def _split_code_aware(text: str) -> list[tuple[str, str]]:
    """把章节文本拆成有序单元：("text", 段落) / ("code", 围栏代码块)。

    代码块保持原子性（不被段落聚合与句子切分破坏）；未闭合围栏视为代码到文末。
    """
    units: list[tuple[str, str]] = []
    buf: list[str] = []
    code_buf: list[str] | None = None

    def flush_text() -> None:
        t = "\n".join(buf).strip()
        if t:
            for p in (x.strip() for x in re.split(r"\n\s*\n", t) if x.strip()):
                units.append(("text", p))
        buf.clear()

    for line in text.split("\n"):
        if line.strip().startswith(CODE_FENCE):
            if code_buf is None:
                flush_text()
                code_buf = [line]
            else:
                code_buf.append(line)
                units.append(("code", "\n".join(code_buf).strip()))
                code_buf = None
        elif code_buf is not None:
            code_buf.append(line)
        else:
            buf.append(line)
    if code_buf is not None:
        units.append(("code", "\n".join(code_buf).strip()))
    else:
        flush_text()
    return units


def _split_code_block(block: str, header: str, max_tokens: int) -> list[str]:
    """超长代码块按行硬切（保留语法结构），每片前置 header 语义锚。"""
    head = f"{header}\n" if header else ""
    head_toks = count_tokens(head)
    pieces: list[str] = []
    cur: list[str] = []
    cur_toks = 0
    for ln in block.split("\n"):
        t = count_tokens(ln)
        if cur and cur_toks + t + head_toks > max_tokens:
            pieces.append(head + "\n".join(cur))
            cur, cur_toks = [], 0
        cur.append(ln)
        cur_toks += t
    if cur:
        pieces.append(head + "\n".join(cur))
    return pieces


def _chunk_section(text: str) -> list[str]:
    """章节内切片核心：散文段落聚合至目标 token，代码块原子成片，跨块重叠。"""
    units = _split_code_aware(text)
    if not units:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    last_chunk_text = ""
    last_prose_line = ""  # 最近的散文行：作为后续代码块的语义锚

    def flush() -> None:
        nonlocal current, current_tokens, last_chunk_text
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
        last_chunk_text = chunks[-1]
        current = []
        current_tokens = 0

    for kind, unit in units:
        if kind == "code":
            flush()
            toks = count_tokens(unit) + (count_tokens(last_prose_line) if last_prose_line else 0)
            if toks > MAX_TOKENS:
                chunks.extend(_split_code_block(unit, last_prose_line, MAX_TOKENS))
                last_chunk_text = chunks[-1]
            else:
                chunks.append(f"{last_prose_line}\n{unit}" if last_prose_line else unit)
            last_prose_line = ""
            continue

        para = unit
        para_tokens = count_tokens(para)
        if para_tokens > MAX_TOKENS:
            flush()
            for sentence in _split_sentences(para):
                if sentence:
                    chunks.append(sentence)
            last_prose_line = para.split("\n")[0][:80]
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
        last_prose_line = para.split("\n")[0][:80]

    flush()

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
