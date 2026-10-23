# PharmaOpt
**Pharmacy inventory decision support: see what to buy, how much, and when.**

Most inventory tools show what you have. PharmaOpt shows what to *do next* and why.

## Features
- **Expiry and stockout risk** using FEFO (first-expiry-first-out) batch simulation
- **Budget-aware purchase plan** with a plain-language reason for each order
- **What-if simulator:** compare not buying, buying now, or buying later
- **Ask PharmaOpt:** natural-language assistant. Numbers come only from the deterministic engine; the LLM (Qwen2.5-7B via Ollama) only explains them
- Invoice text/OCR review with date and quantity validation before stock is added

## Architecture
React UI -> FastAPI -> `engine.py` (forecast / risk / optimizer / simulator) <- `llm.py` (question -> verified facts -> explanation)

## Run locally
```bash
# backend
cd pharmaopt/backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && uvicorn app.main:app --reload
# frontend (new terminal)
cd pharmaopt/frontend && npm install && npm run dev
```
Optional LLM: `ollama pull qwen2.5:7b-instruct`, then `export OLLAMA_URL=http://localhost:11434` before starting the backend.

## Tests
`cd pharmaopt/backend && python -m pytest`

## Deploy
Backend: Render or Railway using `pharmaopt/backend/Dockerfile`. Frontend: Vercel, with `VITE_API_URL` set to the backend URL.

## Note
Medicine data is synthetic. This is decision support; a pharmacist makes the final call.
The demand-scaled generator seeds new databases only. Existing database contents are preserved and are not automatically replaced.

## Run everything with Docker (PostgreSQL + API + UI)
`docker compose -f pharmaopt/docker-compose.yml up --build`, then open http://localhost:8080 (API docs at http://localhost:8000/docs).

## Invoice-to-inventory
Paste invoice lines or upload a photo. OCR (Tesseract) is used for images. Lines look like `Paracetamol 500mg  B123  500  2027-03-31`; tab- and pipe-separated columns are also accepted. Expiry formats are `YYYY-MM-DD`, `DD/MM/YYYY`, and `MM/YYYY`. Impossible dates and nonpositive quantities are rejected and shown for correction; matched lines still require pharmacist review before addition.

## Benchmark
`cd pharmaopt/backend && python benchmark.py` regenerates [docs/benchmark.md](docs/benchmark.md). It compares PharmaOpt with reorder-point and order-up-to-30-day baselines across held-out stochastic demand, with confidence intervals. The data is synthetic, so results do not establish real-world impact.

## Deploy (free tiers)
1. **Database + API on Render:** create a PostgreSQL instance, then a Docker Web Service with root directory `pharmaopt/backend`. Set `DATABASE_URL` to the database's internal URL.
2. **UI on Vercel:** import the repo, set root directory to `pharmaopt/frontend`, and set `VITE_API_URL` to your Render API URL (for example, `https://pharmaopt-api.onrender.com`, with no trailing slash).
3. **LLM (optional):** set `OLLAMA_URL` to a server running `qwen2.5:7b-instruct`. Without it the assistant uses template explanations.
