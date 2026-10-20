# Software Architecture Document (SAD)

**Project:** AUTOSAR HLD Document Analysis & Verification Assistant  
**Student:** Pranav Jai S S (Register No: 127003193)  
**Degree:** B.Tech CSE (AIML) — SASTRA Deemed University  

---

## 1. System Overview

The AUTOSAR HLD Document Analysis Assistant is an advanced AI engineering platform designed to automate the ingestion, semantic search, architectural extraction, consistency checking, and revision comparison of automotive software specifications.

The application is architected around the **C4 Architectural Model**:
1. **Context Level:** Automotive software engineers and system architects interact via a browser-based Streamlit UI to query AUTOSAR specifications and verify HLD models.
2. **Container Level:** Streamlit frontend/controller, local Ollama LLM runtime, Qdrant vector database (Docker container), and PostgreSQL/pgvector database (Docker container).
3. **Component Level:** `AutosarLoader`, `AutosarSplitter`, `StructuredExtractor`, `ConsistencyValidator`, `ModelDiffer`, and `PlantUmlRenderer`.
4. **Code Level:** Python modules adhering to strict typing, error handling, and unit-tested functional boundaries.

---

## 2. Component Descriptions

```
+--------------------------------------------------------------------------------+
|                             Streamlit Application                              |
|                              (Code/app.py)                                     |
|  - Ingestion Dashboard: PDF upload, page extraction status, chunk index counts |
|  - Chat Assistant: Grounded Q&A with inline citations and evidence expanders  |
|  - Architecture Extractor: JSON schema extraction for SWCs, Ports, Interfaces  |
|  - PlantUML Visualizer: Component & sequence diagrams                          |
|  - Revision Review: Side-by-side model diffing between specification versions |
|  - Benchmark Harness: Multi-question evaluation runner                         |
+--------------------------------------------------------------------------------+
             |                                                  |
             v                                                  v
+----------------------------------+          +----------------------------------+
|      Ingestion & Processing      |          |       Vector DB & Knowledge      |
|  - AutosarLoader                 |          |  - Qdrant Vector DB              |
|    * pypdf + pdfplumber          |          |    * Project-isolated collection |
|    * table header replication    |          |    * Cosine distance metric      |
|    * Tesseract OCR fallback      |          |  - Embedders                     |
|  - AutosarSplitter               |          |    * all-MiniLM-L6-v2 (384-dim)  |
|    * 1200 char chunk / 200 ovlp  |          |    * nomic-embed-text (768-dim)  |
|    * section heading segmenter   |          |    * validate_embedding wrapper  |
|  - remove_empty_documents        |          |  - PostgreSQL / PgVector         |
|    * Eliminates Qdrant 422 error |          |    * Session chat history        |
+----------------------------------+          +----------------------------------+
```

### 2.1 Document Ingestion (`autosar_rag/autosar_loader.py`)
- Reads PDF bytes without altering original stream pointers.
- Computes cryptographic SHA-256 signatures to bind document versions.
- Extracts structured tables via `pdfplumber`, prefixing cell contents with column headers to preserve context across chunks.
- Activates OCR for scanned pages lacking text layers.
- Flags empty or whitespace pages with `empty_after_extraction`.

### 2.2 Semantic Chunking (`autosar_rag/autosar_splitter.py`)
- Employs heuristic section segmentation using AUTOSAR heading patterns (`_HEADING_RE`).
- Applies recursive character splitting within section boundaries.
- Generates reproducible, deterministic chunk hashes based on `document_id`, `page_number`, `offset`, and content.
- Applies `remove_empty_documents` to purge blank chunks prior to indexing.

### 2.3 Retrieval & Assistant Knowledge (`assistant/assistant.py`)
- Interfaces with local Qdrant collections namespaced by `autosar_rag_{project_slug}_{model_slug}`.
- Enforces strict vector validation using `validate_embedding` to ensure vector dimensions match configurations and contain finite floating-point numbers.
- Manages chat history and session states in PostgreSQL via `PgAssistantStorage`.

### 2.4 Structured Architecture Extractor (`autosar_rag/structured_extractor.py`)
- Sends document chunks through bounded prompt templates requesting structured JSON.
- Merges chunk-level extractions into a unified architecture model containing:
  - Software Components (SWCs)
  - Ports (Provided/Required, Client-Server/Sender-Receiver)
  - Interfaces and Data Elements
  - Component Dependencies
  - Functional Execution Flows

### 2.5 Consistency Validator (`autosar_rag/validator.py`)
- Audits extracted architecture models against 5 formal consistency rules.
- Generates categorized findings (Errors, Warnings, Info) with source evidence links.

### 2.6 PlantUML Diagram Generator (`posthdl/puml2img.py`)
- Converts structured architecture dictionaries into PlantUML syntax.
- Compiles diagrams to high-resolution PNGs via the bundled `plantuml-1.2024.7.jar`.
