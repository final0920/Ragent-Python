"""文本分块（纯函数，可单测）。"""

from __future__ import annotations

# 自然边界优先级：段落 > 行 > 中文句末 > 中文逗号 > 空格。
_BOUNDARIES = ("\n\n", "\n", "。", "！", "？", "，", " ")


def _split_point(text: str, start: int, target_end: int) -> int:
    """在 [start, target_end] 区间内寻找最靠后的自然边界切点。

    返回切点(含边界字符)的结束下标(exclusive)。找不到则回退到 target_end(硬切)。
    """
    if target_end >= len(text):
        return len(text)
    window = text[start:target_end]
    for sep in _BOUNDARIES:
        pos = window.rfind(sep)
        if pos > 0:  # pos==0 切点过小无意义
            return start + pos + len(sep)
    return target_end


def fixed_size_chunk(text: str, size: int = 512, overlap: int = 128) -> list[str]:
    """按自然边界回退切分：块长≈size、相邻块重叠≈overlap，过滤空块。"""
    if not text:
        return []
    if size <= 0:
        return [text.strip()] if text.strip() else []
    overlap = max(0, min(overlap, size - 1))

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        target_end = min(start + size, n)
        end = _split_point(text, start, target_end)
        if end <= start:  # 安全兜底，避免死循环
            end = target_end
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        # 下一块起点回退 overlap，制造重叠
        start = max(end - overlap, start + 1)
    return chunks


def structure_aware_chunk(
    text: str, target: int = 1400, max_size: int = 1800, min_size: int = 600
) -> list[str]:
    """结构感知分块(Markdown 友好)：按块(段落/标题)贪心打包到 target 附近。

    超长单块回退定长切；过小尾块并入上一块。
    """
    if not text or not text.strip():
        return []
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    chunks: list[str] = []
    buf = ""
    for b in blocks:
        if len(b) > max_size:  # 超长块单独定长切
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.extend(fixed_size_chunk(b, size=max_size, overlap=0))
            continue
        candidate = f"{buf}\n\n{b}" if buf else b
        if len(candidate) <= max_size:
            buf = candidate
            if len(buf) >= target:
                chunks.append(buf)
                buf = ""
        else:
            if buf:
                chunks.append(buf)
            buf = b
    if buf:
        if chunks and len(buf) < min_size and len(chunks[-1]) + len(buf) <= max_size:
            chunks[-1] = chunks[-1] + "\n\n" + buf
        else:
            chunks.append(buf)
    return chunks


def chunk_text(text: str, strategy: str = "fixed_size", size: int = 512, overlap: int = 128) -> list[str]:
    """按策略分发分块。strategy: fixed_size | structure_aware。"""
    if strategy == "structure_aware":
        return structure_aware_chunk(text)
    return fixed_size_chunk(text, size=size, overlap=overlap)
