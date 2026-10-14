"""Compose a cited answer from tool outputs and retrieved chunks (extractive, no LLM needed)."""
from __future__ import annotations

import re

from .retrieval import Hit, tokenize
from .textutil import split_sentences

BADGE = {
    "official": "official page",
    "daad_mirror": "DAAD database mirror",
    "aggregator": "third-party aggregator, verify",
    "reference": "reference note",
}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in split_sentences(text) if len(s.split()) >= 4]


def pick_sentences(query: str, hits: list[Hit], max_sentences: int = 4) -> list[tuple[str, int]]:
    q = set(tokenize(query))
    scored = []
    for hi, h in enumerate(hits[:4]):
        for s in _sentences(h.chunk.text):
            toks = set(tokenize(s))
            overlap = len(q & toks)
            if overlap >= min(2, len(q)):
                scored.append((overlap / (len(toks) ** 0.5), hi, s))
    scored.sort(key=lambda x: -x[0])
    chosen, seen = [], set()
    for _, hi, s in scored:
        if s in seen:
            continue
        seen.add(s)
        chosen.append((s, hi))
        if len(chosen) >= max_sentences:
            break
    chosen.sort(key=lambda x: x[1])
    return chosen


def render_sources(hits: list[Hit], used: list[int]) -> str:
    lines = []
    for hi in sorted(set(used)):
        c = hits[hi].chunk
        stale = " (superseded page version)" if c.status == "superseded" else ""
        lines.append(f"[{hi + 1}] {c.university}, {c.program}, {c.section}. {BADGE.get(c.source_type, c.source_type)}{stale}, scraped {c.scraped_on}. {c.source_url}")
    return "\n".join(lines)


def compose_rag_answer(query: str, hits: list[Hit], max_sentences: int = 4) -> tuple[str, list[int]]:
    chosen = pick_sentences(query, hits, max_sentences)
    if not chosen:
        return "", []
    body = " ".join(f"{s} [{hi + 1}]" for s, hi in chosen)
    return body, [hi for _, hi in chosen]
