# Financial Model Generator

A **local-first** application that converts annual report PDFs into structured, formula-driven Excel financial models.

Upload PDFs → Extract tables → Map line items → Generate 3-statement Excel model — all processed locally, nothing leaves your machine.

---

## Architecture

```
Vercel (Frontend: React + TypeScript)
        ↓  API calls to localhost
Local Machine (Backend: FastAPI + Python)
        ├── SQLite database
        ├── PDF extraction (Docling / pdfplumber)
        ├── Financial statement detection
        ├── Line-item mapper (56-item standard schema)
        └── projects_data/ (PDFs, extraction artifacts)
```

---

## Phases Implemented

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project management, PDF upload, dashboard | ✅ Done |
| 2 | PDF extraction (Docling + pdfplumber fallback) | ✅ Done |
| 3 | Statement detection + line-item mapping | ✅ Done |
| 4 | Historical model engine | 🔜 Next |
| 5 | Forecast + Excel export | 🔜 Planned |
| 6 | Local AI assistant (Ollama/llama.cpp) | 🔜 Planned |

---

## Local Setup (Backend)

### Prerequisites
- Python 3.10+

### Steps

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

Backend runs at **http://localhost:8000**  
API docs at **http://localhost:8000/docs**

> **Note:** Docling is the primary PDF extractor. If it fails to install on your machine, the app automatically falls back to `pdfplumber`.

---

## Frontend Setup (Local Development)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:3000** and proxies `/api` → `localhost:8000`.

---

## Deploy Frontend to Vercel

### Option A — Vercel CLI (quickest)

```bash
cd frontend
npm i -g vercel
vercel login       # use rahul.mittal@analecglobal.com
vercel             # follow prompts, set root to frontend/
vercel --prod
```

### Option B — GitHub + Automatic Deploys

1. Push this repo to GitHub under your account.
2. Go to [vercel.com](https://vercel.com) → **Add New Project** → import the GitHub repo.
3. Set **Root Directory** to `frontend`.
4. Add environment variable:
   ```
   VITE_API_URL = http://localhost:8000
   ```
5. Deploy. Every push to `main` triggers an automatic redeploy.

### GitHub Secrets (for CI/CD via Actions)

In your GitHub repo → **Settings → Secrets and variables → Actions**, add:

| Secret | Where to find it |
|--------|-----------------|
| `VERCEL_TOKEN` | vercel.com → Account Settings → Tokens |
| `VERCEL_ORG_ID` | vercel.com → Account Settings → General → Team ID |
| `VERCEL_PROJECT_ID` | vercel.com → Project Settings → General → Project ID |

---

## Usage Workflow

1. **Open the app** (Vercel URL or `localhost:3000`)
2. **Create a project** — enter company name, ticker, sector, currency
3. **Upload PDFs** — drag & drop 1–10 annual report PDFs
4. **Extract** — click Extract on each document; tables are detected automatically
5. **Review tables** — visit Document Review to correct statement type assignments
6. **Run Mapping** — maps extracted line items to the 56-item standard schema
7. **Review Mappings** — approve/reject/edit individual line items; bulk-approve high-confidence ones
8. *(Phase 5)* **Generate Excel** — produces a fully formulaed .xlsx workbook

---

## Project Structure

```
financial-model-generator/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Settings
│   ├── database.py                # SQLite + SQLAlchemy
│   ├── models.py                  # ORM models
│   ├── schemas.py                 # Pydantic schemas
│   ├── requirements.txt
│   ├── routers/
│   │   ├── projects.py            # CRUD for projects
│   │   ├── documents.py           # Upload + file management
│   │   ├── extraction.py          # PDF extraction (Phase 2)
│   │   └── mapping.py             # Line-item mapping (Phase 3)
│   ├── services/
│   │   ├── pdf_extractor.py       # Docling + pdfplumber
│   │   ├── statement_detector.py  # IS / BS / CF classification
│   │   ├── line_item_mapper.py    # Rules-based mapper
│   │   └── financial_schema.py    # Schema loader + matcher
│   └── data/
│       └── financial_schema.yaml  # 56-item standard schema
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── Home.tsx            # Project list
    │   │   ├── ProjectDetail.tsx   # Upload + pipeline
    │   │   ├── DocumentReview.tsx  # Table review
    │   │   └── MappingReview.tsx   # Line-item review
    │   ├── components/
    │   ├── api/client.ts           # Axios API client
    │   └── types/index.ts
    ├── vercel.json
    └── package.json
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all projects |
| POST | `/api/projects` | Create project |
| DELETE | `/api/projects/{id}` | Delete project |
| POST | `/api/projects/{id}/documents` | Upload PDF |
| POST | `/api/projects/{id}/documents/{docId}/extract` | Start extraction |
| GET | `/api/projects/{id}/documents/{docId}/tables` | Get extracted tables |
| POST | `/api/projects/{id}/run-mapping` | Run line-item mapping |
| GET | `/api/projects/{id}/line-items` | List mapped items |
| PATCH | `/api/projects/{id}/line-items/{itemId}` | Update mapping |
| POST | `/api/projects/{id}/line-items/bulk-approve` | Bulk approve |
| GET | `/health` | Health check |

Full interactive docs: **http://localhost:8000/docs**
