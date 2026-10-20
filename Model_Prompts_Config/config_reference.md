# Model & Infrastructure Configuration Reference

**Student:** Pranav Jai S S (127003193)  
**Institution:** SASTRA Deemed University  
**Project:** AUTOSAR HLD Document Analysis Assistant  

---

## 1. Supported LLMs and Embedding Models

| Model Type | Identifier | Host / Provider | Vector Dimensions | Recommended Use |
| :--- | :--- | :--- | :--- | :--- |
| **LLM (Primary)** | `qwen2.5-coder:1.5b` | Ollama (Local) | N/A | Code & architecture extraction, local privacy |
| **LLM (Alternative)** | `llama3:8b` | Ollama (Local) | N/A | High-capacity reasoning |
| **LLM (Cloud Optional)**| `openrouter/anthropic/claude-3.5-sonnet` | OpenRouter API | N/A | Complex edge-case resolution |
| **Embedder (Default)** | `all-minilm` (`all-MiniLM-L6-v2`) | Ollama (Local) | **384** | Fast, lightweight semantic retrieval |
| **Embedder (Alternative)**| `nomic-embed-text` | Ollama (Local) | **768** | Higher retrieval capacity |
| **Embedder (Cloud)** | `openrouter/...` | OpenRouter API | **1024** | Cloud embeddings |

---

## 2. Qdrant Collection Isolation & Safety Guards

The assistant isolates vector collections per project and embedding model to avoid cross-project contamination and dimension mismatches:

```python
effective_collection = f"autosar_rag_{project_slug}_{model_slug}"
```

### Safety Guards Implemented:
1. **Empty Document Filtering (`remove_empty_documents`):** Filters out empty pages, whitespace chunks, and scan artifacts before chunking and before embedding.
2. **Embedding Vector Validation (`validate_embedding`):** Validates all vectors returning from the embedding adapter to guarantee:
   - Vector is not None and `len(vector) > 0`
   - Vector length equals the configured dimension (e.g. 384 or 768)
   - Vector values are finite floating-point numbers (no NaN or Inf values)
