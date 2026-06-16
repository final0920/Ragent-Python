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
