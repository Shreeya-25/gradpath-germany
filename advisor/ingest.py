"""Load markdown source documents and split them into section-aware chunks with metadata."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path

from .config import RAW_DIR, MAX_CHUNK_WORDS
from .textutil import split_sentences


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    university: str
    program: str
    city: str
    doc_type: str
    section: str
    text: str
    source_url: str
    source_type: str
    status: str
    scraped_on: str
    language_of_instruction: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def search_text(self) -> str:
        # Header prefix lets the program/section name match queries even when the body doesn't repeat them.
        return f"{self.university} {self.program} {self.section}. {self.text}"


def parse_document(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise ValueError(f"{path.name}: missing front matter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, m.group(2).strip()


def split_sections(body: str) -> list[tuple[str, str]]:
    parts = re.split(r"^## (.+)$", body, flags=re.M)
    sections = []
    # parts = [preamble, title1, body1, title2, body2, ...]
    for i in range(1, len(parts), 2):
        sections.append((parts[i].strip(), parts[i + 1].strip()))
    return sections


def window_text(text: str, max_words: int = MAX_CHUNK_WORDS) -> list[str]:
    """Split on sentence boundaries into windows of at most max_words words."""
    sentences = split_sentences(text)
    windows, cur, count = [], [], 0
    for s in sentences:
        n = len(s.split())
        if cur and count + n > max_words:
            windows.append(" ".join(cur))
            cur, count = [], 0
        cur.append(s)
        count += n
    if cur:
        windows.append(" ".join(cur))
    return windows


def load_chunks(raw_dir: Path = RAW_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(raw_dir.glob("*.md")):
        meta, body = parse_document(path)
        for section, text in split_sections(body):
            for j, piece in enumerate(window_text(text)):
                chunks.append(
                    Chunk(
                        chunk_id=f"{meta['doc_id']}::{re.sub(r'[^a-z0-9]+', '_', section.lower()).strip('_')}::{j}",
                        doc_id=meta["doc_id"],
                        university=meta.get("university", ""),
                        program=meta.get("program", ""),
                        city=meta.get("city", ""),
                        doc_type=meta.get("doc_type", ""),
                        section=section,
                        text=piece,
                        source_url=meta.get("source_url", ""),
                        source_type=meta.get("source_type", "aggregator"),
                        status=meta.get("status", "current"),
                        scraped_on=meta.get("scraped_on", ""),
                        language_of_instruction=meta.get("language_of_instruction", ""),
                    )
                )
    return chunks
