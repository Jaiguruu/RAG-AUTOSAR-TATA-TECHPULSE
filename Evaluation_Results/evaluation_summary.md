# Evaluation Results & Benchmark Summary

**Capstone Project:** AUTOSAR HLD Document Analysis Assistant  
**Student:** Pranav Jai S S (127003193)  
**Institution:** SASTRA Deemed University  

---

## 1. Benchmark Overview

The evaluation suite evaluates the retrieval and factual grounding accuracy of the AUTOSAR RAG pipeline against an audited test dataset covering the **AUTOSAR LargeDataCOM Specification (SWS Release 4.4.0)**.

- **Total Test Cases:** 24 technical questions covering module initialization, PDU buffering, API signatures, error codes, and transmission flows.
- **Evaluation Engine:** `evaluate_dataset.py` executing with dedicated per-run Qdrant collection isolation.
- **Metrics Tracked:**
  - **Keyword / Concept Coverage:** Rigorous exact and multi-phrase scoring (requiring all required concept terms to match).
  - **Retrieval Hit Rate:** Verification that the gold-standard reference section is returned in the top-k retrieved chunks.
  - **Citation Precision:** Presence of verifiable `[DocumentName, p. N]` references matching the actual PDF page numbers.

---

## 2. Benchmark Artifacts in this Directory

| File | Purpose |
| :--- | :--- |
| `baseline_evaluation_report.md` | Comprehensive Markdown report detailing question-by-question scores, test execution parameters, and failure analyses. |
| `baseline_autosar_large_data_com_answers.json` | Complete machine-readable output recording generated answers, latency, retrieved chunk IDs, and evaluation scores. |
| `README.md` | Verification instructions for running the live evaluation harness. |

---

## 3. Running the Live Evaluation

To reproduce or benchmark the evaluation on a new hardware setup:

```bash
# 1. Ensure Ollama, Qdrant, and PostgreSQL are running
# 2. Execute the evaluation script
python evaluate_dataset.py \
    --dataset Input_Data/autosar_large_data_com_test_dataset.json \
    --pdf assets/doc/AUTOSAR_SWS_LargeDataCOM.pdf \
    --model qwen2.5-coder:1.5b \
    --embedder all-minilm \
    --output Evaluation_Results/latest_evaluation_report.json
```
