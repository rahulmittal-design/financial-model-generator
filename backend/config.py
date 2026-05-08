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
