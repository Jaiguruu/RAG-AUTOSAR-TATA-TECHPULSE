# Problem Statement: AUTOSAR HLD Document Analysis Assistant

## 1. Project Overview

**Project name:** AUTOSAR HLD Document Analysis Assistant  
**Domain:** Automotive Engineering AI  
**Project type:** AI-assisted document analysis and architecture knowledge management  
**Recommended delivery stage:** Pilot

The goal is to build a secure AI-assisted application that extracts, organizes, searches, and validates architectural knowledge from AUTOSAR High-Level Design (HLD) documents. The application should help automotive engineering teams understand large architecture documents more efficiently while keeping engineering decisions under human control.

## 2. Background and Problem Context

Automotive software architecture is documented in High-Level Design (HLD) documents. These documents describe:

- Software components
- Interfaces and ports
- Signals
- Dependencies between components
- Functional flows
- Integration logic

HLD documents may be hundreds of pages long and are often maintained as PDFs. Architects, developers, integration engineers, and testers must manually read and interpret these documents to find the information they need.

This manual process creates several problems:

1. **Slow document review:** Engineers spend substantial time locating and understanding relevant information across lengthy documents.
2. **Fragmented architecture knowledge:** Component, interface, signal, and dependency information is spread across document sections, tables, and diagrams rather than available in one structured repository.
3. **Difficult traceability:** It is hard to follow relationships between components, interfaces, signals, functional flows, and downstream engineering activities.
4. **Inconsistency and omissions:** Manual interpretation can miss mismatches, missing dependencies, inconsistent terminology, or incomplete test coverage.
5. **Repeated effort:** Engineers may need to rediscover information that has already been documented or analyzed.
6. **Limited evidence during reviews:** Findings and answers need to be connected to the exact source section or page so engineers can verify them.

The central problem is therefore not simply that HLD documents are long. It is that valuable architecture knowledge is difficult to extract, organize, retrieve, compare, and verify consistently.

## 3. Problem Statement

Design and implement a secure, AI-assisted system that ingests approved AUTOSAR High-Level Design documents and related architecture specifications, converts their contents into structured and searchable architecture knowledge, and enables engineers to ask natural-language questions, inspect component and dependency relationships, compare document revisions, and identify potential inconsistencies.

The system must provide evidence-backed results with page- or section-level citations so that engineers can verify each finding against the source material. It must support engineering review and export of structured findings, but it must **not** autonomously approve architecture decisions, modify original HLD documents without review, or replace formal architecture governance.

## 4. Project Objectives

The system should:

- Reduce the manual effort required to review HLD documents.
- Build a structured, searchable repository of architecture knowledge.
- Extract and organize components, interfaces, ports, signals, and functional flows.
- Improve traceability between components, interfaces, signals, and dependencies.
- Support architecture design reviews, engineer onboarding, impact analysis, and test planning.
- Compare document revisions and report potential inconsistencies or completeness gaps.
- Produce results that engineers can verify, correct, and export.

## 5. Intended Users

Primary users and stakeholders include:

- System architects
- AUTOSAR architects
- Software developers
- Integration engineers
- Test engineers
- Engineering managers

## 6. Inputs

The system should accept approved engineering materials, including:

- AUTOSAR HLD documents
- Interface specifications
- Architecture descriptions
- Component catalogues
- Revision history

Documents may contain text, headings, tables, metadata, and scanned pages. OCR should be supported for scanned pages where required.

## 7. Required Functional Capabilities

### 7.1 Document ingestion

- Allow users to upload or select an approved HLD document.
- Validate supported document types and document/project context.
- Extract text, headings, tables, and metadata.
- Apply OCR to scanned pages when needed.
- Preserve source locations so extracted information can be traced back to the document.

### 7.2 Architecture information extraction

Identify and organize relevant architecture entities, including:

- Components
- Interfaces
- Ports
- Signals
- Functional flows
- Dependencies

The system should represent relationships between these entities where the source documents provide sufficient evidence.

### 7.3 Search and question answering

- Allow engineers to ask questions in natural language.
- Retrieve relevant document sections using architecture context.
- Generate answers grounded in retrieved source evidence.
- Include page- or section-level citations in responses.
- Provide cited summaries and component reports.

### 7.4 Architecture mapping and traceability

- Create component and interface inventories.
- Map dependencies and functional flows.
- Make relevant architecture relationships easier to inspect.
- Support traceability for design review, impact analysis, and test planning.

### 7.5 Revision comparison

- Compare different revisions of HLD documents.
- Highlight relevant changes in architecture information.
- Report potential mismatches, missing dependencies, and inconsistencies for engineer review.

### 7.6 Completeness checks and reporting

- Run checks for potential inconsistencies and completeness gaps.
- Present findings with source evidence.
- Allow engineers to review, correct, and export structured findings.

## 8. Expected Outputs

The system should produce:

- Component and interface inventories
- Dependency maps
- Functional-flow summaries
- Natural-language question-and-answer responses with citations
- Cited document and component summaries
- Revision-comparison results
- Potential inconsistency and completeness reports
- Structured exports for downstream engineering use

Outputs are suggestions and findings for review, not automatic design decisions.

## 9. High-Level Processing Workflow

1. The engineer uploads or selects an approved HLD document.
2. The system extracts text, tables, headings, and metadata, using OCR for scanned pages when necessary.
3. The content is divided into chunks based on document sections and architecture context.
4. Relevant architecture entities and relationships are extracted and organized.
5. Content embeddings are generated and stored in a local vector database with suitable metadata.
6. The engineer submits a natural-language query or requests a report.
7. The system retrieves relevant evidence from the approved project collection.
8. An approved LLM generates a response grounded in the retrieved evidence.
9. The response includes source citations and any relevant confidence or limitation indicators.
10. The engineer reviews, corrects, accepts, or rejects the findings.
11. Approved results can be exported or stored for later use.

## 10. Scope Boundaries

### In scope

- PDF and supported-document ingestion
- OCR for scanned pages
- Extraction of components, interfaces, ports, signals, and flows
- Architecture entity and dependency mapping
- Natural-language search and question answering with citations
- Document and component summaries
- Revision comparison
- Potential inconsistency and completeness reporting
- Structured export of findings

### Out of scope

- Automatic approval of architecture decisions
- Modification of source HLD documents without review
- Replacement of formal architecture governance

## 11. Proposed Technical Direction

The source case study proposes a secure application based on a locally or privately hosted Large Language Model (LLM), Retrieval-Augmented Generation (RAG), local vector storage, and a Python-based web application.

| Layer | Suggested options | Purpose |
|---|---|---|
| User interface | Streamlit; Flask web UI; optional enterprise portal | Upload, search, review, and export |
| API and services | FastAPI or Flask | Application logic and APIs |
| LLM | Any approved model, such as Llama, Mistral, Qwen, DeepSeek, Falcon, or equivalent | Evidence-grounded extraction, summarization, and responses |
| Embeddings | BGE, E5, Sentence Transformers, or equivalent | Convert document content into vectors |
| Vector database | FAISS or ChromaDB; Milvus or self-hosted Weaviate for scale | Local semantic retrieval and metadata filtering |
| RAG orchestration | LangChain, LlamaIndex, or a custom Python pipeline | Retrieval, prompt control, and citations |
| Structured storage | SQLite or PostgreSQL | Projects, users, reviews, approvals, and audit data |
| Ingestion and OCR | PyMuPDF, PDFPlumber, PyPDF, Tesseract, or custom parsers | Parse documents, tables, metadata, and scanned pages |
| Deployment | Docker; optional Kubernetes | Controlled deployment and isolation |

These are options from the source case study, not mandatory technology choices. The final stack should be selected based on evaluation, security, licensing, and infrastructure constraints.

## 12. Non-Functional Requirements and Constraints

### Evidence and reliability
- Answers must be grounded in retrieved approved project documents.
- Responses should include page- or section-level citations.
- Confidence or limitation indicators should be shown where appropriate.
- Engineers must be able to verify findings against source documents.

### Security and access control
- Keep documents, embeddings, prompts, responses, and source material within approved organizational boundaries.
- Separate project collections and enforce role-based access.
- Prevent unauthorized cross-project data exposure.
- Use controlled access, network isolation, and audit logging as appropriate.

### Version and governance control
- Identify document versions and approved-source status.
- Preserve traceability from findings to source evidence.
- Require authorized engineering review before AI-generated content is used for compliance, design approval, software release, or vehicle validation.

### Human oversight
- The application assists engineering judgment; it does not replace it.
- It must not autonomously approve architecture decisions or alter original HLD documents without review.

## 13. Success Metrics

Evaluate the pilot using the following indicative measures:

| Metric | Measurement |
|---|---|
| Document review effort | Percentage reduction against baseline manual review time |
| Extraction quality | Precision and recall for approved architecture entities |
| Answer groundedness | Percentage of responses with valid source citations |
| User adoption | Active users and repeat query volume |
| Issue discovery | Number of confirmed mismatches or missing dependencies identified |

Baseline values and target thresholds should be established during the discovery phase; the source case study does not specify numerical targets.

## 14. Risks and Controls

| Risk | Control |
|---|---|
| Incorrect extraction from tables or diagrams | Use page-level citations and review queues |
| Hallucinated architecture relationships | Restrict answers to retrieved evidence and show confidence or limitations |
| Unauthorized access to project documents | Apply role-based access and project isolation |
| Outdated document versions | Enforce document version labels and approved-source status |

## 15. Implementation Phases

1. **Discovery:** Collect representative HLD documents, define the architecture taxonomy, identify common questions, and establish success metrics.
2. **Pilot:** Build document ingestion, local vector storage, RAG search, a Streamlit interface, and export functionality.
3. **Validation:** Benchmark extraction and question-answering quality with architects and testers.
4. **Scale:** Add revision comparison, graph relationships, access control, and integrations.

## 16. Acceptance Criteria

The pilot can be evaluated against the following criteria, derived from the stated scope and success metrics:

- Users can ingest supported HLD documents, including scanned pages where OCR is needed.
- The system extracts architecture entities and preserves links to their source locations.
- Users can ask natural-language questions and receive answers with page- or section-level citations.
- The system can produce component/interface inventories, dependency maps, and functional-flow summaries.
- The system can compare document revisions and flag potential inconsistencies for human review.
- Findings can be reviewed, corrected, and exported in a structured format.
- Access controls keep project information separated and available only to authorized users.
- AI output is not treated as formal architecture approval.

These criteria make the intended pilot testable. They do not imply that a particular accuracy threshold has already been agreed.

## 17. Example User Scenarios

### Scenario A: Find component information
An AUTOSAR architect asks, “Which components use this interface?” The system retrieves the relevant architecture evidence and returns the identified components with source citations.

### Scenario B: Understand dependencies
An integration engineer asks for the dependencies of a selected component. The system presents the dependencies supported by the HLD and points to the corresponding sections.

### Scenario C: Compare revisions
A developer supplies two approved HLD revisions. The system highlights potential changes to components, interfaces, signals, or dependencies and links each finding to source evidence.

### Scenario D: Identify completeness gaps
A test engineer requests a review of a functional flow. The system reports possible missing dependencies or incomplete information that should be checked by an engineer.

These scenarios illustrate intended behavior; actual findings depend on the information present in the supplied documents.

## 18. Governance Rule

**All AI-generated findings must remain traceable to approved source material and be reviewed by authorized engineering specialists before they are used for compliance, design approval, software release, or vehicle validation.**

## 19. Reference

Prepared from **Automotive Engineering AI: Standard Project Case Study Document**, Version 1.0, September 2026, **Case Study 1: AUTOSAR HLD Document Analysis Assistant**, pages 4–7. The technology options, project scope, risks, success metrics, and implementation phases above are based on that case study. The acceptance criteria and example user scenarios are structured clarifications derived from its stated requirements, not additional requirements explicitly specified by the source.
