"""Optional LLM generation. Disabled unless ANTHROPIC_API_KEY is set and the `anthropic` package is installed.
NOTE: not exercised in the offline build environment; the default extractive composer is what the tests cover."""
from __future__ import annotations

import os

from .retrieval import Hit

SYSTEM = (
    "You are a careful advisor for international master's applicants to German universities. "
    "Answer ONLY from the numbered context and tool results. Cite sources as [n]. "
    "If sources conflict or the context is insufficient, say so plainly. Never invent deadlines or requirements. "
    "Tell the user to verify on the official university page."
)


def available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def llm_answer(question: str, hits: list[Hit], tool_summary: str) -> str | None:
    if not available():
        return None
    import anthropic

    ctx = "\n\n".join(
        f"[{i + 1}] ({h.chunk.university}, {h.chunk.program}, {h.chunk.section}; {h.chunk.source_type}; {h.chunk.status})\n{h.chunk.text}"
        for i, h in enumerate(hits[:5])
    )
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        max_tokens=700,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Question: {question}\n\nTool results:\n{tool_summary}\n\nContext:\n{ctx}"}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
