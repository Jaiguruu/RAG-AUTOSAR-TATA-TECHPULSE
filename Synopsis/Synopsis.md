# Capstone Project Synopsis

**Project Title:** AUTOSAR High-Level Design (HLD) Document Analysis & Verification Assistant Using Retrieval-Augmented Generation (RAG)  
**Student Name:** Pranav Jai S S  
**Register Number:** 127003193  
**Degree & Specialization:** B.Tech Computer Science and Engineering  
**Institution:** SASTRA Deemed University, Thanjavur, Tamil Nadu  

---

## 1. Abstract

Modern automotive software development adheres strictly to AUTOSAR (AUTomotive Open System ARchitecture) standards, which encompass thousands of pages of Software Component (SWC), Basic Software (BSW), and High-Level Design (HLD) specifications. Verification, inconsistency detection, and architecture extraction across multi-revision AUTOSAR documents are traditionally manual, labor-intensive, and prone to costly integration errors.

This capstone project presents an end-to-end, privacy-preserving, enterprise-grade AI assistant powered by Retrieval-Augmented Generation (RAG), local Large Language Models (LLMs), and high-performance vector search (Qdrant). The system ingests complex AUTOSAR technical PDFs, preserves strict page-level and section-level provenance, extracts structured architectural models (components, ports, interfaces, signals, and functional flows), performs rule-based consistency validation, generates interactive PlantUML architectural diagrams, and facilitates automated revision comparison between document versions.

---

## 2. Problem Statement

1. **Volume and Complexity:** AUTOSAR Software Specifications (SWS) are dense, technical, and tabular documents spanning hundreds of pages. Engineers spend disproportionate time cross-referencing interface definitions, signal mappings, and API signatures.
2. **Hallucination Risk in Automotive Systems:** Standard general-purpose LLMs hallucinate non-existent API signatures, invalid port directions, or fabricated page references, which is intolerable in safety-critical ISO 26262 automotive environments.
3. **Multi-Revision Drift:** Engineering changes between document revisions frequently introduce silent mismatches—such as renamed ports, missing interfaces, or type alterations—that escape manual review.
4. **Data Privacy & IP Protection:** Proprietary automotive software architectures cannot be leaked to public cloud LLMs, necessitating locally deployable, on-premise solutions.
5. **Vector Ingestion Fragility:** Complex PDFs often produce blank pages or empty text chunks that cause downstream vector databases (e.g., Qdrant) to fail with `422 Unprocessable Entity: dense vector must not be empty` errors.

---

## 3. Objectives and Key Deliverables

- **High-Fidelity Document Ingestion:** Develop a specialized PDF loader (`AutosarLoader`) leveraging `pypdf`, `pdfplumber`, and Tesseract OCR to extract running text, structured tables with semantic headers, and heading hierarchies with full cryptographic provenance (SHA-256).
- **Architecture-Aware Semantic Chunking:** Implement `AutosarSplitter` with recursive character chunking (1,200 chars / 200 overlap), section segmentation, and proactive empty-document filtering (`remove_empty_documents`) to guarantee zero empty vectors reach the database.
- **Strictly Grounded RAG Assistant:** Integrate local LLMs (via Ollama, prioritizing `qwen2.5-coder:1.5b`) with Qdrant vector database and PgVector session storage, enforcing strict citation policies (`[DocumentName, p. N]`).
- **Structured Architecture Extraction:** Extract formal JSON schemas of SWCs, Client-Server/Sender-Receiver interfaces, data elements, and functional flows from the document text.
- **Rule-Based Consistency Validator:** Automate detection of orphaned interfaces, invalid port directions, malformed signal mappings, and unresolved component dependencies.
- **Automated Revision Comparison:** Enable direct PDF-to-PDF or model-to-model differential analysis highlighting added, removed, and modified architectural elements.
- **Visual Architecture Synthesis:** Dynamically render PlantUML component and sequence diagrams directly from extracted architecture models.
- **Reproducible Evaluation Harness:** Implement an isolated benchmark harness executing all 24 questions from the AUTOSAR LargeDataCOM test dataset with keyword coverage metrics and full retrieval trace logs.

---

## 4. System Architecture & Methodology

```
+-------------------------------------------------------------------------------+
|                             Streamlit Web UI                                  |
|   [Chat & Evidence]  [Architecture Extraction]  [Diff Review]  [Evaluation]   |
+-------------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------------+
|                       Ingestion & Chunking Pipeline                           |
|  1. AutosarLoader (pypdf + pdfplumber tables + Tesseract OCR + SHA-256)       |
|  2. AutosarSplitter (RecursiveCharacterTextSplitter + Section Segmentation)    |
|  3. Empty Document Filter (remove_empty_documents -> Eliminates Qdrant 422)   |
+-------------------------------------------------------------------------------+
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
+-----------------------------+   +---------------------------------------------+
|    Embedding & Storage      |   |            Architecture & Analysis          |
|  - OllamaEmbedder           |   |  - StructuredExtractor (LLM JSON Schemas)   |
|    (all-MiniLM / nomic)     |   |  - ConsistencyValidator (Rule-Based Engine) |
|  - validate_embedding Guard |   |  - PlantUML Visualizer (Component Diagrams) |
|  - Qdrant Vector DB         |   |  - ModelDiffer (Revision Comparison)        |
|  - PgVector Session DB      |   +---------------------------------------------+
+-----------------------------+
```

---

## 5. Key Innovations and Solutions

1. **Defensive Vector Pipeline:** Root-cause analysis and definitive fix for the Qdrant 422 error by implementing `remove_empty_documents` across loader, splitter, and UI pipelines, alongside runtime `validate_embedding` wrappers preventing invalid vectors.
2. **Table Header Replication:** Enhanced table extraction in `AutosarLoader` that replicates header labels for each cell in every row, preventing loss of semantic context across chunk boundaries.
3. **Audited Grounding:** Answers are displayed alongside the exact retrieved source snippets, page numbers, and cosine relevance scores, allowing engineers to verify grounding before accepting outputs.
4. **Deterministic Revision Comparison:** Normalized, order-insensitive JSON diffing that categorizes changes across components, ports, interfaces, and signals with line-by-line inspection.

---

## 6. Evaluation & Results

- **Benchmark Dataset:** 24 technical questions derived from the official AUTOSAR SWS LargeDataCOM specification.
- **Evaluation Isolation:** Dynamic, per-run collection isolation bound to the PDF SHA-256 hash, dataset hash, and embedding model slug.
- **Automated Scoring:** Multi-keyword and strict phrase matching evaluating retrieval accuracy and answer relevance with full JSON retrieval tracing.

---

## 7. Conclusion

The AUTOSAR HLD Document Analysis & Verification Assistant bridges the gap between massive, dense automotive software specifications and agile engineering verification. By combining robust document parsing, defensive vector indexing, local LLMs, and formal validation, the system accelerates engineering review cycles while maintaining the strict rigor demanded by automotive software standards.
