"""Retrieval evaluation. A question counts as a hit at k when one of the top-k chunks comes from the
expected document AND contains the evidence string. Reports hit@1, hit@3, hit@5 and MRR per method."""
from __future__ import annotations

import json
from collections import defaultdict

from .config import EVAL_FILE, ROOT
from .ingest import load_chunks
from .retrieval import HybridRetriever
from .tools import find_program, load_programs

METHODS = ["bm25", "tfidf", "hybrid", "hybrid_rerank"]


def evaluate(retriever: HybridRetriever, questions: list[dict], method: str, k: int = 5) -> dict:
    progs = load_programs()
    ranks, misses = [], []
    for q in questions:
        hint_prog = hint_uni = None
        if method == "hybrid_rerank":
            pids = find_program(q["question"])
            if len(pids) == 1:
                hint_prog, hint_uni = progs[pids[0]]["program"], progs[pids[0]]["university"]
            elif pids:
                hint_uni = progs[pids[0]]["university"]
        hits = retriever.search(q["question"], k=k, method=method, program_hint=hint_prog, university_hint=hint_uni)
        rank = None
        for h in hits:
            if h.chunk.doc_id == q["expected_doc"] and q["evidence"] in h.chunk.text.lower():
                rank = h.rank
                break
        ranks.append(rank)
        if rank is None:
            misses.append(q["question"])
    n = len(questions)
    return {
        "hit@1": sum(1 for r in ranks if r == 1) / n,
        "hit@3": sum(1 for r in ranks if r and r <= 3) / n,
        "hit@5": sum(1 for r in ranks if r and r <= 5) / n,
        "mrr": sum(1 / r for r in ranks if r) / n,
        "misses": misses,
    }


def main() -> dict:
    questions = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    retriever = HybridRetriever(load_chunks())
    results = {m: evaluate(retriever, questions, m) for m in METHODS}
    lines = [f"Evaluation on {len(questions)} hand-written questions over {len(retriever.chunks)} chunks\n",
             "| Method | Hit@1 | Hit@3 | Hit@5 | MRR |", "|---|---|---|---|---|"]
    for m, r in results.items():
        lines.append(f"| {m} | {r['hit@1']:.2f} | {r['hit@3']:.2f} | {r['hit@5']:.2f} | {r['mrr']:.2f} |")
    report = "\n".join(lines)
    print(report)
    for m, r in results.items():
        if r["misses"]:
            print(f"\nMisses for {m}:")
            for q in r["misses"]:
                print("  -", q)
    (ROOT / "eval" / "results.md").write_text(report + "\n", encoding="utf-8")
    (ROOT / "eval" / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    main()
