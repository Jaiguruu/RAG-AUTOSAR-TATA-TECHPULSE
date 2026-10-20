# AUTOSAR HLD Document Analysis Assistant

A local-first Streamlit application for searching AUTOSAR specifications, extracting architecture entities, reviewing potential consistency gaps, and comparing document revisions. AI-generated answers and findings are review candidates, not formal engineering approvals.

## What is included

- Page-level PDF text extraction with source metadata; optional OCR for low-text pages.
- Table extraction through `pdfplumber`, with rows rendered so values retain their column labels.
- Section-aware recursive chunking (default 1,200 characters, 200-character overlap) with reproducible chunk IDs.
- RAG question answering with retrieved source passages displayed for manual verification.
- Structured extraction of components, interfaces, ports, signals, functional flows, dependencies, and source evidence.
- Conservative consistency findings and field-level architecture revision comparison.
- A benchmark evaluator that rebuilds an isolated Qdrant collection for the exact source PDF and dataset, stores retrieval traces, and labels keyword coverage as a proxy rather than factual accuracy.
- Automated tests for loader/splitter behavior, evaluation scoring, extraction validation, section detection, and revision comparison.

## Requirements

- Python 3.10 or newer (source uses modern Python type syntax).
- Docker, for local PostgreSQL/pgvector and Qdrant services.
- Ollama for local LLM and embedding models, unless configured for a supported remote provider.
- Tesseract OCR executable for scanned-page OCR. Python packages alone do not install this OS-level binary.

## Setup

1. Create and activate a virtual environment.

   ```bash
   python -m venv .venv
   # Linux/macOS
   source .venv/bin/activate
   # Windows PowerShell: .venv\\Scripts\\Activate.ps1
   ```

2. Install the pinned Python dependencies.

   ```bash
   pip install -r cookbook/requirements.txt
   ```

3. Configure local services and secrets.

   ```bash
   cp .env.example .env
   ```

   Change the placeholder passwords/keys. Never commit `.env`. `DATABASE_URL`, `QDRANT_URL`, and `QDRANT_API_KEY` must match the services you start. The application defaults `AUTOSAR_PROJECT_ID` to `local`; deployments needing multiple projects must assign trusted project IDs and add authentication/authorization at the hosting layer.

4. Pull the default local models.

   ```bash
   ollama pull qwen2.5-coder:1.5b
   ollama pull all-minilm:l6-v2
   ```

5. Start PostgreSQL/pgvector and Qdrant using the included helper scripts. For shell-based setup, export `.env` first:

   ```bash
   set -a && . ./.env && set +a
   ./cookbook/run_pgvector.sh
   ./cookbook/run_qdrant.sh
   ```

6. Start the app.

   ```bash
   streamlit run app.py
   ```

7. Upload a permitted PDF, index it, ask questions, and inspect the retrieved passages. For architecture extraction, run the Architecture tab. For revisions, upload two PDF files (or validated architecture JSON files). For evaluation, use the Evaluation tab or run the command below.

## Evaluation

Run the full reference benchmark (default is all questions):

```bash
python evaluate_dataset.py
```

Run a quick smoke subset:

```bash
python evaluate_dataset.py --limit 3
```

Run one known benchmark question:

```bash
python evaluate_dataset.py --question-id LDCOM-005
```

The evaluator hashes the PDF and dataset and rebuilds a dedicated evaluation collection. It writes `autosar_large_data_com_answers.json` and `evaluation_report.md`. **Keyword coverage is not factual accuracy.** A strong score does not by itself prove factual correctness, citation validity, or architecture completeness. Review each answer against the cited source and use the saved retrieval trace to diagnose misses.

## Tests

```bash
python -m pytest -q
python -m compileall -q app.py assistant autosar_rag evaluate_dataset.py
```

The loader/splitter integration tests require `langchain-core` and `langchain-text-splitters`, which are included in `cookbook/requirements.txt`. Tests involving actual Ollama, PostgreSQL and Qdrant services require those services to be running and are not replaced by unit tests.

## Important limitations

- The configured project namespace isolates collections, but this repository does not implement a full multi-user authentication and role-based authorization system. Deploy behind an authenticated boundary and enforce project authorization before production use.
- OCR only runs when the optional Python dependencies and the Tesseract executable are available. OCR output and tables still require human review for engineering-critical use.
- Retrieved passages are displayed as evidence candidates. An LLM-generated citation is not automatically verified to support the associated claim.
- Architecture extraction depends on the selected LLM and source quality. Failed chunks are reported; no extracted findings does not imply completeness or compliance.
- Revision diffs compare extracted models. Extraction omissions can create false changes or hide real ones, so review both model coverage and source evidence.
- The benchmark metric reports keyword coverage only. Do not claim a target accuracy until it is demonstrated on a manually verified benchmark.

## Project map

- `app.py` — Streamlit user interface and workflows.
- `assistant/assistant.py` — RAG assistant, embeddings, storage, and collection configuration.
- `autosar_rag/autosar_loader.py` — PDF, table, OCR, and provenance handling.
- `autosar_rag/autosar_splitter.py` and `sectioning.py` — section-aware chunking.
- `autosar_rag/structured_extractor.py` — structured entity extraction and evidence attachment.
- `autosar_rag/validator.py` — potential consistency findings and revision comparison.
- `autosar_rag/evaluation_metrics.py` and `evaluate_dataset.py` — benchmark scoring, source isolation, and reports.
- `tests/` — unit and integration-oriented tests.
- `FINAL_FIX_REPORT.md` — changes, verification status, and remaining gaps.
