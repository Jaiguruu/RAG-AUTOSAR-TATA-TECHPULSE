# Evaluation artifacts

`baseline_evaluation_report.md` and `baseline_autosar_large_data_com_answers.json` are the existing baseline outputs from the uploaded repository. They cover 10 questions and report 32% keyword coverage. They are preserved as baseline evidence, not presented as results from the patched implementation.

Run `python evaluate_dataset.py` from the project root to regenerate current outputs at the project root using the full benchmark dataset by default. Copy the resulting report and JSON into this folder only after reviewing the run metadata, source/dataset hashes, all 24 question IDs, and per-question retrieval traces. Never manually edit reported scores.

Keyword coverage is a diagnostic proxy, not factual accuracy or citation groundedness. See `../FINAL_FIX_REPORT.md` for validation scope and remaining limitations.
