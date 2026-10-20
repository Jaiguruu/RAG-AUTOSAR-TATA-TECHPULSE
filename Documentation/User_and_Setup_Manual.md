# User and Setup Manual

**Project:** AUTOSAR HLD Document Analysis & Verification Assistant  
**Student:** Pranav Jai S S (127003193)  
**Institution:** SASTRA Deemed University  

---

## 1. Prerequisites and System Requirements

- **Operating System:** Windows 10/11, macOS, or Ubuntu Linux 20.04+
- **Python:** Python 3.10+ (Python 3.11/3.12 recommended)
- **Container Runtime:** Docker Desktop / Docker Engine (for PostgreSQL and Qdrant)
- **Local LLM Engine:** Ollama (from [ollama.ai](https://ollama.ai))
- **Java Runtime:** JRE 11+ (required for PlantUML diagram rendering)
- **Tesseract OCR (Optional):** Required only if OCR on scanned image PDFs is needed.

---

## 2. Installation and Environment Setup

### Step 1: Clone the Repository and Navigate to Code
```bash
git clone <repository_url>
cd SASTRAUniversity_PranavJaiSS_127003193_CSx_AIML/Code
```

### Step 2: Create and Activate a Python Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r cookbook/requirements.txt
```

### Step 4: Configure Environment Variables
Copy the configuration template to `.env`:
```bash
cp ../Model_Prompts_Config/environment_template.env .env
```
Ensure `.env` matches your local service ports and credentials:
```ini
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/autosar_rag
QDRANT_URL=http://localhost:6333
AUTOSAR_PROJECT_ID=local
EMBEDDING_DIMENSIONS=384
```

---

## 3. Starting Supporting Services

### Start Ollama and Pull Required Models
```bash
# Pull primary coding & architecture model
ollama pull qwen2.5-coder:1.5b

# Pull default embedding model
ollama pull all-minilm
```

### Start Qdrant and PostgreSQL Containers
```bash
# Start PostgreSQL / PgVector
docker run -d --name pgvector -p 5432:5432 \
  -e POSTGRES_DB=autosar_rag \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  pgvector/pgvector:pg16

# Start Qdrant Vector Database
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

---

## 4. Running the Application

Launch the Streamlit web interface:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 5. User Walkthrough

1. **Document Ingestion:**
   - In the sidebar, select your LLM model (`qwen2.5-coder:1.5b`) and Embedder (`all-minilm`).
   - Drag and drop your AUTOSAR PDF specification.
   - The system processes pages, extracts tables, filters empty chunks, and indexes vectors into Qdrant.
2. **Grounded Q&A Chat:**
   - Ask technical questions (e.g., *"What is the function signature for Com_SendSignal?"*).
   - Inspect the retrieved evidence candidates and inline citations (`[Document, p. N]`).
3. **Architecture Extraction:**
   - Navigate to the **Architecture Extraction** tab.
   - Click **Run extraction** to generate structured components, ports, and interfaces.
4. **PlantUML Visualization:**
   - Generate and download auto-generated component diagrams.
5. **Revision Comparison:**
   - In the **Revision Review** tab, upload two PDF versions (or models) to view highlighted additions, deletions, and modifications.
