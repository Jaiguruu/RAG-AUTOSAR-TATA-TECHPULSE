# Input Data & Benchmark Datasets

**Capstone Project:** AUTOSAR HLD Document Analysis Assistant  
**Student:** Pranav Jai S S (127003193)  
**Institution:** SASTRA Deemed University  

---

## 1. Directory Contents

This directory contains the input datasets and documentation for the AUTOSAR High-Level Design (HLD) specifications used to evaluate and benchmark the RAG assistant.

| File / Folder | Description |
| :--- | :--- |
| `autosar_large_data_com_test_dataset.json` | The benchmark evaluation dataset containing 24 technical questions, reference answers, and evaluation criteria covering AUTOSAR LargeDataCOM SWS. |
| `AUTOSAR_SWS_LargeDataCOM.pdf` (User Supplied) | The standard AUTOSAR Software Specification PDF for Large Data Communication (Release 4.4.0 / Classic Platform). |

---

## 2. Benchmark Dataset Structure (`autosar_large_data_com_test_dataset.json`)

The evaluation JSON contains structured question-answer pairs with grading criteria:

```json
{
  "test_cases": [
    {
      "id": "TC_001",
      "question": "What is the primary purpose of the Large Data COM module in AUTOSAR?",
      "expected_concepts": [
        "large data transmission",
        "serialization",
        "COM module extension"
      ],
      "reference_section": "1.1 Scope of this Document",
      "reference_page": 6
    }
  ]
}
```

---

## 3. Legal and Redistribution Guidelines for AUTOSAR Specifications

1. **AUTOSAR Copyright Notice:** AUTOSAR specifications are copyrighted by the AUTOSAR development partnership. In compliance with institutional policies and AUTOSAR terms of use, proprietary or copyrighted OEM/Tier-1 HLD PDFs are not bundled in public repositories.
2. **Obtaining Official Documents:** Official AUTOSAR specifications are freely accessible to registered users directly from the [AUTOSAR Official Website](https://www.autosar.org/standards/classic-platform).
3. **Placing Input Documents:** To index documents locally in the application:
   - Place your target PDF under `Code/assets/doc/` or upload it directly through the Streamlit web interface (`http://localhost:8501`).
