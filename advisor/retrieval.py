"""Hybrid retrieval: BM25 + TF-IDF (word and char n-grams) fused with Reciprocal Rank Fusion,
followed by a metadata-aware reranker (program match, source reliability, freshness).
An optional dense retriever (sentence-transformers) plugs in when the package is installed."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .config import RRF_K, SOURCE_WEIGHT, SUPERSEDED_PENALTY
from .ingest import Chunk

OLD_RE = re.compile(r"\b(older|previous|previously|old version|superseded|outdated|cached|2025)\b", re.I)

STOPWORDS = set(
    "a an and are as at be by can do does for from has have how i in is it me my of on or the this that to was what when which who will with you your".split()
)


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9äöüß]+", text.lower())
    out = []
    for t in toks:
        if t in STOPWORDS:
            continue
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        out.append(t)
    return out


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = docs
        self.doc_len = np.array([len(d) for d in docs], dtype=float)
        self.avgdl = self.doc_len.mean() if len(docs) else 0.0
        self.tf = [Counter(d) for d in docs]
        df: Counter = Counter()
        for d in docs:
            df.update(set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        s = np.zeros(len(self.docs))
        for t in set(query_tokens):
            if t not in self.idf:
                continue
            for i, tf in enumerate(self.tf):
                f = tf.get(t, 0)
                if f:
                    denom = f + self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                    s[i] += self.idf[t] * f * (self.k1 + 1) / denom
        return s


@dataclass
class Hit:
    chunk: Chunk
    score: float
    rank: int


def _rank(scores: np.ndarray) -> list[int]:
    return list(np.argsort(-scores, kind="stable"))


class HybridRetriever:
    def __init__(self, chunks: list[Chunk], use_dense: bool = False, dense_model: str = "BAAI/bge-small-en-v1.5"):
        self.chunks = chunks
        texts = [c.search_text for c in chunks]
        self.bm25 = BM25([tokenize(t) for t in texts])
        self.word_tfidf = TfidfVectorizer(tokenizer=tokenize, lowercase=False, ngram_range=(1, 2), sublinear_tf=True, token_pattern=None)
        self.word_mat = self.word_tfidf.fit_transform(texts)
        self.char_tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        self.char_mat = self.char_tfidf.fit_transform(texts)
        self.dense = None
        if use_dense:
            try:
                from sentence_transformers import SentenceTransformer  # optional dependency

                self.dense = SentenceTransformer(dense_model)
                self.dense_mat = self.dense.encode(texts, normalize_embeddings=True)
            except Exception as exc:  # pragma: no cover
                print(f"[warn] dense retriever disabled: {exc}")
                self.dense = None

    # ----- individual retrievers -----
    def bm25_scores(self, q: str) -> np.ndarray:
        return self.bm25.scores(tokenize(q))

    def tfidf_scores(self, q: str) -> np.ndarray:
        w = (self.word_mat @ self.word_tfidf.transform([q]).T).toarray().ravel()
        c = (self.char_mat @ self.char_tfidf.transform([q]).T).toarray().ravel()
        return 0.6 * w + 0.4 * c

    def dense_scores(self, q: str) -> np.ndarray:
        v = self.dense.encode([q], normalize_embeddings=True)[0]
        return self.dense_mat @ v

    # ----- fusion -----
    def fuse(self, q: str, methods: tuple[str, ...] = ("bm25", "tfidf")) -> np.ndarray:
        fused = np.zeros(len(self.chunks))
        for m in methods:
            s = getattr(self, f"{m}_scores")(q)
            for r, idx in enumerate(_rank(s)):
                if s[idx] > 0:
                    fused[idx] += 1.0 / (RRF_K + r + 1)
        return fused

    # ----- public API -----
    def search(
        self,
        query: str,
        k: int = 5,
        method: str = "hybrid_rerank",
        program_hint: str | None = None,
        university_hint: str | None = None,
        include_superseded: bool = False,
    ) -> list[Hit]:
        if method == "bm25":
            scores = self.bm25_scores(query)
        elif method == "tfidf":
            scores = self.tfidf_scores(query)
        else:
            methods = ("bm25", "tfidf") + (("dense",) if self.dense is not None else ())
            scores = self.fuse(query, methods)
            if method == "hybrid_rerank":
                scores = self.rerank(scores, program_hint, university_hint, bool(OLD_RE.search(query)))
        mask = np.ones(len(self.chunks), dtype=bool)
        if not include_superseded and method == "hybrid_rerank":
            # superseded pages stay searchable but are demoted by rerank(); only hard-drop if asked
            pass
        order = [i for i in _rank(np.where(mask, scores, -1)) if scores[i] > 0][:k]
        return [Hit(self.chunks[i], float(scores[i]), r + 1) for r, i in enumerate(order)]

    def rerank(self, scores: np.ndarray, program_hint: str | None, university_hint: str | None, asks_for_old: bool = False) -> np.ndarray:
        out = scores.copy()
        for i, c in enumerate(self.chunks):
            # RRF scores are nearly flat between adjacent ranks, so source reliability only
            # acts as a mild tie-breaker (official > mirror > aggregator), not a hard re-sort.
            mult = 1 - 0.1 * (1 - SOURCE_WEIGHT.get(c.source_type, 0.7))
            if c.status == "superseded" and not asks_for_old:
                mult *= SUPERSEDED_PENALTY
            if program_hint and c.program.lower() == program_hint.lower():
                mult *= 1.6
            elif university_hint and c.university.lower() == university_hint.lower():
                mult *= 1.25
            elif (program_hint or university_hint) and c.doc_type != "reference":
                mult *= 0.8
            out[i] *= mult
        return out
