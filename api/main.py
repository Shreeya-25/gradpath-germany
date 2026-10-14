"""FastAPI backend:  uvicorn api.main:app --reload"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from advisor import tools as T
from advisor.agent import Advisor

app = FastAPI(title="Germany Program Advisor", version="0.1.0")
advisor = Advisor()


class ProfileIn(BaseModel):
    country: str = "India"
    degree_field: str = "Artificial Intelligence and Machine Learning"
    cgpa: float | None = 8.4
    scale: float = 10.0
    gre_quant: int | None = None
    gre_awa: float | None = None
    english_test_done: bool | None = None
    aps_done: bool | None = None


class AskIn(BaseModel):
    question: str
    profile: ProfileIn = ProfileIn()


@app.get("/health")
def health():
    return {"status": "ok", "chunks": len(advisor.chunks), "programs": len(T.load_programs())}


@app.get("/programs")
def programs():
    return [{"program_id": k, "university": v["university"], "program": v["program"]} for k, v in T.load_programs().items()]


@app.post("/ask")
def ask(body: AskIn):
    res = advisor.run(body.question, T.Profile(**body.profile.model_dump()))
    return {"answer": res.answer, "sources": res.sources, "intents": res.intents, "programs": res.programs,
            "tool_calls": [{"tool": c["tool"], "args": c["args"]} for c in res.tool_calls]}


@app.post("/eligibility/{program_id}")
def eligibility(program_id: str, profile: ProfileIn):
    if program_id not in T.load_programs():
        raise HTTPException(404, "unknown program_id")
    return T.check_eligibility(T.Profile(**profile.model_dump()), program_id).to_dict()


@app.get("/deadlines/{program_id}")
def deadlines(program_id: str, semester: str = "winter", year: int = 2027):
    if program_id not in T.load_programs():
        raise HTTPException(404, "unknown program_id")
    return T.get_deadlines(program_id, semester, year, date.today())
