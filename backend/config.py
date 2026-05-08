import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "projects_data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{BASE_DIR}/app.db"

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://*.vercel.app",
    "*",
]

MAX_FILE_SIZE_MB = 100
SUPPORTED_EXTENSIONS = {".pdf"}

EXTRACTION_CONFIDENCE_THRESHOLD = 0.5
MAPPING_AUTO_APPROVE_THRESHOLD = 0.85

# ── LLM config ────────────────────────────────────────────────────────────────
LLM_CACHE_DIR = BASE_DIR / "llm_cache"
LLM_CACHE_DIR.mkdir(exist_ok=True)

os.environ.setdefault("HF_HOME", str(LLM_CACHE_DIR))
os.environ.setdefault("TRANSFORMERS_CACHE", str(LLM_CACHE_DIR / "hub"))

LLM_DEFAULT_MODEL = "Qwen/Qwen2.5-3B-Instruct"
LLM_LARGE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
LLM_SMALL_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
