# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Environment Setup
- **Dependencies**: Install libraries using `pip install -r cookbook/requirements.txt`.
- **Infrastructure**: Run the infrastructure (PgVector and Qdrant) using the provided shell scripts:
  - `./cookbook/run_pgvector.sh`
  - `./cookbook/run_qdrant.sh`

### Development
- **Run Application**: Start the Streamlit application with `streamlit run app.py`.
- **Ollama**: Ensure Ollama is running and the required models (`llama3` and `nomic-embed-text`) are pulled.

## Architecture

This project is an AUTOSAR document assistant with RAG (Retrieval-Augmented Generation) capabilities.

- **`autosar_rag/`**: Contains core RAG logic:
  - `AutosarLoader`: Handles ingestion of AUTOSAR documents.
  - `AutosarSplitter`: Splits documents into chunks for RAG.
  - `StructuredExtractor`: Extracts structured data from AUTOSAR files.
  - `ConsistencyValidator`: Validates the data.
- **`assistant/`**: Logic for the RAG assistant implementation.
- **`app.py`**: The Streamlit frontend entry point.
- **`cookbook/`**: Contains helper scripts for infrastructure and project setup.
