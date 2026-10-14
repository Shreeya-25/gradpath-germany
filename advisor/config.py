from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROGRAMS_JSON = ROOT / "data" / "programs.json"
EVAL_FILE = ROOT / "eval" / "questions.json"

MAX_CHUNK_WORDS = 120
TOP_K = 5
RRF_K = 60

# Source reliability used for ranking and for the badge shown in answers.
SOURCE_WEIGHT = {"official": 1.0, "reference": 0.9, "daad_mirror": 0.85, "aggregator": 0.6}
SUPERSEDED_PENALTY = 0.35
