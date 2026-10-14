"""Deterministic agent tools. Everything here is rule-based on data/programs.json,
so results are reproducible and each check cites the source document it came from."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import date
from functools import lru_cache

from .config import PROGRAMS_JSON


@dataclass
class Profile:
    name: str = ""
    country: str = "India"
    degree_field: str = "Artificial Intelligence and Machine Learning"
    cgpa: float | None = 8.4
    scale: float = 10.0
    gre_quant: int | None = None
    gre_awa: float | None = None
    gate_cs_qualified: bool | None = None
    english_test_done: bool | None = None
    aps_done: bool | None = None


@lru_cache(maxsize=1)
def load_programs() -> dict:
    data = json.loads(PROGRAMS_JSON.read_text(encoding="utf-8"))
    return {p["program_id"]: p for p in data["programs"]}


def find_program(text: str) -> list[str]:
    """Return program_ids whose alias appears in text (longest alias wins per program)."""
    t = text.lower().replace("ü", "u").replace("ue", "u") if False else text.lower()
    t = t.replace("ü", "ue")
    found: dict[str, int] = {}
    for pid, p in load_programs().items():
        for alias in p["aliases"]:
            a = alias.lower()
            if a in t:
                found[pid] = max(found.get(pid, 0), len(a))
    # drop programs matched only by a short generic alias when a longer alias of the same university matched
    ranked = sorted(found.items(), key=lambda kv: -kv[1])
    if not ranked:
        return []
    best_len = ranked[0][1]
    return [pid for pid, ln in ranked if ln >= min(best_len, 6)] if len(ranked) > 1 else [ranked[0][0]]


# ---------------------------------------------------------------- grade conversion
def _bavarian(n_d: float, n_max: float, n_min: float) -> float:
    g = 1 + 3 * (n_max - n_d) / (n_max - n_min)
    return round(max(1.0, g), 2)


def convert_cgpa_to_german(cgpa: float, scale: float = 10.0) -> dict:
    """Estimate the German grade (1.0 best, 4.0 lowest pass) with two common methods.
    The official conversion is done by uni-assist / the university and can differ."""
    methods = {}
    methods["direct_scale (N_max=scale, N_min=40% of scale)"] = _bavarian(cgpa, scale, 0.4 * scale)
    if abs(scale - 10.0) < 1e-9:
        pct = (cgpa - 0.75) * 10  # VTU CGPA->percentage formula
        methods["via_percentage (VTU formula, N_max=100, N_min=40)"] = _bavarian(pct, 100.0, 40.0)
        pct_note = round(pct, 1)
    else:
        pct_note = None
    vals = list(methods.values())
    return {
        "cgpa": cgpa,
        "scale": scale,
        "percentage_vtu": pct_note,
        "methods": methods,
        "estimate_low": min(vals),
        "estimate_high": max(vals),
        "caveat": "Estimate only (modified Bavarian formula). The university or uni-assist makes the official conversion.",
        "source": "grade_conversion_reference",
    }


# ---------------------------------------------------------------- eligibility
@dataclass
class Check:
    name: str
    status: str  # pass | likely | risk | fail | todo | unknown | info
    detail: str
    source: str = ""


@dataclass
class EligibilityReport:
    program_id: str
    program: str
    university: str
    verdict: str
    checks: list[Check] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def check_eligibility(profile: Profile, program_id: str) -> EligibilityReport:
    p = load_programs()[program_id]
    req = p["requirements"]
    src = p["doc_ids"][0]
    checks: list[Check] = []

    # 1) degree field
    field_l = (profile.degree_field or "").lower()
    kws = req.get("degree_keywords", [])
    if kws:
        if any(k in field_l for k in kws):
            checks.append(Check("Degree field", "likely", f"'{profile.degree_field}' matches the expected field. Requirement: {req['degree']}.", src))
        else:
            checks.append(Check(
                "Degree field", "risk",
                f"Requirement: {req['degree']}. Your degree ('{profile.degree_field}') is not a direct name match, so the committee will compare your curriculum module by module.",
                src))

    # 2) grade
    thr = req.get("min_german_grade")
    if profile.cgpa is not None:
        conv = convert_cgpa_to_german(profile.cgpa, profile.scale)
        lo, hi = conv["estimate_low"], conv["estimate_high"]
        if thr is None:
            checks.append(Check("Minimum grade", "unknown", f"No published minimum grade in the captured sources. Your estimated German grade is {lo} to {hi}.", "grade_conversion_reference"))
        elif hi <= thr:
            checks.append(Check("Minimum grade", "pass", f"Required: {thr} or better. Your estimate {lo} to {hi} meets it under both methods.", src))
        elif lo > thr:
            checks.append(Check("Minimum grade", "fail", f"Required: {thr} or better. Your estimate {lo} to {hi} is worse under both methods.", src))
        else:
            checks.append(Check("Minimum grade", "risk", f"Required: {thr} or better. Your estimate is {lo} to {hi}: it passes under one conversion method and fails under the other, so it is borderline. Ask the university which conversion it applies.", src))

    # 3) GRE / GATE
    if profile.country in req.get("gre_or_gate_countries", []):
        gq, ga = req.get("gre_quant_min"), req.get("gre_awa_min")
        if profile.gate_cs_qualified:
            checks.append(Check("GRE/GATE", "pass", "GATE CS score reported; it must meet that year's minimum qualifying score.", src))
        elif profile.gre_quant is None:
            checks.append(Check("GRE/GATE", "todo", f"Required for your country: GRE Quant >= {gq} and Analytical Writing >= {ga}, or a qualifying GATE CS score. You have not entered a score.", src))
        else:
            ok = profile.gre_quant >= gq and (profile.gre_awa or 0) >= ga
            checks.append(Check("GRE/GATE", "pass" if ok else "fail", f"Required GRE Quant >= {gq}, AWA >= {ga}. You entered Quant {profile.gre_quant}, AWA {profile.gre_awa}.", src))
    elif req.get("gre_required"):
        checks.append(Check("GRE", "todo", "A third-party listing says the GRE General Test is mandatory. Verify on the official page.", src))

    # 4) APS
    if profile.country in req.get("aps_countries", []):
        if profile.aps_done:
            checks.append(Check("APS certificate", "pass", "APS certificate reported as done.", src))
        else:
            checks.append(Check("APS certificate", "todo", "An APS certificate is required for applicants with a bachelor's degree from your country.", src))

    # 5) uni-assist
    if req.get("uni_assist_vpd") is True:
        checks.append(Check("uni-assist VPD", "todo", "A preliminary documentation (VPD) from uni-assist is required in addition to the university application.", src))
    elif req.get("uni_assist_vpd") is False:
        checks.append(Check("uni-assist VPD", "info", "One listing says uni-assist is not required; confirm on the official page.", src))

    # 6) English
    if req.get("english_proof"):
        status = "pass" if profile.english_test_done else "todo"
        checks.append(Check("English proficiency", status, "Proof of English proficiency is required.", src))

    # 7) credits
    if req.get("min_ects"):
        checks.append(Check("Bachelor credits", "unknown", f"Bachelor's must have at least {req['min_ects']} ECTS (6 semesters). Check your transcript's credit total.", src))

    statuses = {c.status for c in checks}
    if "fail" in statuses:
        verdict = "Does not meet at least one published requirement."
    elif "risk" in statuses:
        verdict = "Possible, but at least one requirement is borderline or needs committee review."
    elif statuses & {"todo", "unknown"}:
        verdict = "No blocking issue found; some items still need action or verification."
    else:
        verdict = "Meets the published requirements found in the sources."
    return EligibilityReport(program_id, p["program"], p["university"], verdict, checks)


# ---------------------------------------------------------------- deadlines
def get_deadlines(program_id: str, semester: str = "winter", year: int = 2027, today: date | None = None) -> dict:
    today = today or date.today()
    p = load_programs()[program_id]
    d = p.get("deadlines", {}).get(semester)
    if not d:
        return {"program_id": program_id, "program": p["program"], "semester": semester, "found": False,
                "message": "No deadline captured in the sources; check the university page."}

    def to_date(mm_dd: str) -> date:
        m, dd = mm_dd.split("-")
        return date(year, int(m), int(dd))

    out = {
        "program_id": program_id, "program": p["program"], "university": p["university"],
        "semester": semester, "found": True, "intake_year": year,
        "deadline": to_date(d["close"]).isoformat(), "confidence": d["confidence"],
        "note": d.get("note", ""), "source": d["source"],
        "basis": "Month and day come from the source page; the year assumes the same annual pattern, so confirm once the new cycle opens.",
    }
    if d.get("recommended_close_for_visa"):
        out["recommended_for_visa_applicants"] = to_date(d["recommended_close_for_visa"]).isoformat()
    if d.get("open"):
        out["opens"] = to_date(d["open"]).isoformat()
    out["days_left"] = (to_date(d["close"]) - today).days
    return out


# ---------------------------------------------------------------- checklist
def document_checklist(program_id: str, profile: Profile | None = None) -> dict:
    p = load_programs()[program_id]
    docs = list(p.get("required_documents", []))
    if profile and profile.country != "India":
        docs = [d for d in docs if "India" not in d]
    return {"program_id": program_id, "program": p["program"], "university": p["university"],
            "documents": docs, "source": p["doc_ids"][0],
            "note": "Compiled from the program page; the official page is the final authority."}
