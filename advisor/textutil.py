import re

_ABBREV = ["B.Sc.", "M.Sc.", "B.Eng.", "e.g.", "i.e.", "approx.", "etc.", "vs.", "Dr.", "Prof."]


def split_sentences(text: str) -> list[str]:
    """Sentence splitter that does not break on common abbreviations like B.Sc. or e.g."""
    protected = text
    for i, a in enumerate(_ABBREV):
        protected = protected.replace(a, f"@@{i}@@")
    parts = re.split(r"(?<=[.!?])\s+", protected.strip())
    out = []
    for p in parts:
        for i, a in enumerate(_ABBREV):
            p = p.replace(f"@@{i}@@", a)
        if p:
            out.append(p)
    return out
