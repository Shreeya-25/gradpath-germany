"""Tool-calling agent. A router decides which tools to run (grade conversion, eligibility,
deadlines, checklist), retrieval always runs for grounding, and the composer merges everything
into one cited answer. The node structure (route -> tools -> retrieve -> compose) maps 1:1 onto a
LangGraph graph if you want to port it."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from . import tools as T
from .compose import compose_rag_answer, render_sources
from .ingest import load_chunks
from .llm import llm_answer
from .retrieval import HybridRetriever

INTENTS = {
    "grade": r"\b(cgpa|gpa|german grade|bavarian|grade convert|convert my)\b|convert.*grade",
    "eligibility": r"eligib|can i apply|do i qualify|am i (eligible|qualified)|chance|will i get|meet(s)? the requirement|can i get (in|into)|accept",
    "deadline": r"deadline|last date|when (do|can|should) i apply|application (period|window)|how much time|days left",
    "documents": r"document|checklist|what do i need|required (docs|papers)|papers|what to submit|upload",
}


@dataclass
class AgentResult:
    question: str
    answer: str
    intents: list[str]
    programs: list[str]
    tool_calls: list[dict] = field(default_factory=list)
    sources: str = ""
    hits: list = field(default_factory=list)


class Advisor:
    def __init__(self, use_dense: bool = False, use_llm: bool = False):
        self.chunks = load_chunks()
        self.retriever = HybridRetriever(self.chunks, use_dense=use_dense)
        self.use_llm = use_llm

    # --- nodes ---
    @staticmethod
    def route(question: str) -> list[str]:
        q = question.lower()
        return [name for name, pat in INTENTS.items() if re.search(pat, q)]

    def run(self, question: str, profile: T.Profile | None = None, today: date | None = None) -> AgentResult:
        profile = profile or T.Profile()
        intents = self.route(question)
        pids = T.find_program(question)
        progs = T.load_programs()
        calls: list[dict] = []
        parts: list[str] = []
        tool_summary: list[str] = []

        # tools
        if "grade" in intents and profile.cgpa is not None:
            r = T.convert_cgpa_to_german(profile.cgpa, profile.scale)
            calls.append({"tool": "convert_cgpa_to_german", "args": {"cgpa": profile.cgpa, "scale": profile.scale}, "result": r})
            m = "; ".join(f"{k}: {v}" for k, v in r["methods"].items())
            line = (f"Estimated German grade for CGPA {r['cgpa']}/{r['scale']:g}: {r['estimate_low']} to {r['estimate_high']} (1.0 is best, 4.0 is the lowest pass). "
                    f"Methods: {m}. {r['caveat']}")
            parts.append(line); tool_summary.append(line)

        if "eligibility" in intents:
            targets = pids or ["tum_informatics", "tuebingen_ml", "saarland_dsai", "rwth_sse"]
            for pid in targets:
                rep = T.check_eligibility(profile, pid)
                calls.append({"tool": "check_eligibility", "args": {"program_id": pid}, "result": rep.to_dict()})
                lines = [f"{rep.university}, {rep.program}: {rep.verdict}"]
                for c in rep.checks:
                    lines.append(f"  - {c.name} [{c.status}]: {c.detail}")
                parts.append("\n".join(lines)); tool_summary.append("\n".join(lines))

        if "deadline" in intents:
            sem = "summer" if re.search(r"summer|april|sose", question.lower()) else "winter"
            targets = pids or list(progs.keys())
            for pid in targets:
                d = T.get_deadlines(pid, sem, 2027, today)
                calls.append({"tool": "get_deadlines", "args": {"program_id": pid, "semester": sem}, "result": d})
                if d["found"]:
                    extra = f" Recommended for visa applicants: {d['recommended_for_visa_applicants']}." if d.get("recommended_for_visa_applicants") else ""
                    note = f" Note: {d['note']}." if d.get("note") else ""
                    line = (f"{d['university']}, {d['program']} ({sem} {d['intake_year']}): deadline {d['deadline']} "
                            f"({d['days_left']} days from today), confidence {d['confidence']}.{extra}{note}")
                else:
                    line = f"{d['program']}: {d['message']}"
                parts.append(line); tool_summary.append(line)

        if "documents" in intents:
            targets = pids or ["tum_informatics"]
            for pid in targets:
                c = T.document_checklist(pid, profile)
                calls.append({"tool": "document_checklist", "args": {"program_id": pid}, "result": c})
                if c["documents"]:
                    line = f"Documents for {c['university']}, {c['program']}: " + "; ".join(c["documents"]) + "."
                    parts.append(line); tool_summary.append(line)

        # retrieval (always, for grounding and citations)
        program_hint = progs[pids[0]]["program"] if len(pids) == 1 else None
        university_hint = progs[pids[0]]["university"] if pids else None
        hits = self.retriever.search(question, k=5, program_hint=program_hint, university_hint=university_hint)
        body, used = compose_rag_answer(question, hits, max_sentences=2 if parts else 4)

        answer_parts = []
        if parts:
            answer_parts.append("\n\n".join(parts))
        llm_text = llm_answer(question, hits, "\n".join(tool_summary)) if self.use_llm else None
        if llm_text:
            answer_parts = [llm_text]
            used = list(range(min(5, len(hits))))
        elif body:
            answer_parts.append("From the sources: " + body)
        if not answer_parts:
            answer = ("I could not find this in my sources. I only cover the master's programs in my dataset "
                      "(TU Munich, RWTH Aachen, Saarland, Tuebingen), so please check the university's official page.")
        else:
            answer = "\n\n".join(answer_parts)
        answer += "\n\nAdmission rules change every cycle. Verify on the official university page before applying."
        return AgentResult(question, answer, intents, pids, calls, render_sources(hits, used) if used else "", hits)
