# Capstone Submission Checklist

The repository is packaged in runnable developer-root form to preserve its current relative paths. Copy/organize it into the institution's required folder structure only after using a clean extracted copy to verify the application still runs.

Suggested top-level submission structure (replace placeholders with your actual institutional details):

```text
UniversityName_StudentName_RegisterNo_CSx_AI/
├── Synopsis/
├── Input_Data/
├── Code/                  # Complete runnable project root, including assets/ and cookbook/
├── Model_Prompts_Config/
├── Evaluation_Results/
├── Documentation/
├── Video/
└── Declarations/
```

## Before submission

- [ ] Replace the folder-name placeholders with the exact required institutional naming format.
- [ ] Put the complete runnable repository under `Code/`; preserve relative folders such as `assets/`, `assistant/`, `autosar_rag/`, `cookbook/`, and `tests/`.
- [ ] Include only data that you are permitted to redistribute. Follow institutional rules for source AUTOSAR PDFs.
- [ ] Include the project synopsis, architecture/design document, user/setup guide, limitations, and test report.
- [ ] Include prompt/schema configuration without API keys, passwords, or `.env` secrets.
- [ ] Run `python -m pytest -q` and `python -m compileall -q app.py assistant autosar_rag evaluate_dataset.py` in the packaged code folder.
- [ ] Run the live evaluation after Ollama, PostgreSQL, and Qdrant are configured. Include the generated result JSON and report; do not hand-edit metrics.
- [ ] Complete the institution's actual declarations. Do not submit template declarations as signed evidence.
- [ ] Record a real walkthrough showing PDF ingestion, citation inspection, architecture extraction, revision comparison, evaluation output, and known limitations.
- [ ] Zip the complete folder, extract it into a clean location, and follow the setup guide from scratch.

See `FINAL_FIX_REPORT.md` for what was changed, what was tested, and what remains unverified.
