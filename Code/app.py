"""Streamlit UI for the AUTOSAR RAG assistant."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
from phi.document import Document
from phi.utils.log import logger

from assistant.assistant import get_rag_assistant
from autosar_rag.autosar_loader import AutosarLoader
from autosar_rag.autosar_splitter import AutosarSplitter, remove_empty_documents
from autosar_rag.structured_extractor import StructuredExtractor
from autosar_rag.validator import ConsistencyValidator
from posthdl.puml2img import generate_plantuml_image

# ---------------------------------------------------------------------------
# Page setup and paths
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AUTOSAR Assistant | TATA Techpulse",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
PUML_TEMPLATE_PATH = ASSETS_DIR / "autosar_basic.puml"
LOGO_PATH = ASSETS_DIR / "robot_autosar.jpeg"
PROCESSED_UPLOADS_KEY = "processed_upload_hashes"
INDEXED_CHUNKS_KEY = "indexed_source_chunks"
ARCH_RESULT_KEY = "architecture_result"
MAX_UPLOAD_BYTES = int(os.getenv("MAX_PDF_UPLOAD_BYTES", str(50 * 1024 * 1024)))

SUGGESTED_QUESTIONS = [
    "Summarize the responsibilities of the LdCom module.",
    "Which configuration parameters does the PduR module define?",
    "/bd Show the layered architecture of the basic software.",
]

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --paper: #EDEFF1;
  --side: #E4E8EB;
  --surface: #F8F9FA;
  --ink: #1D262D;
  --muted: #5B6872;
  --line: #CDD3D8;
  --line-strong: #A9B3BB;
  --accent: #0F5C7A;
  --accent-ink: #FFFFFF;
  --ok: #2E7D4F;
  --bad: #B3261E;
  --radius: 3px;
}

/* Typography: target text elements only so icon fonts keep working */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
.stApp button, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp [data-baseweb="select"], .stApp [data-testid="stMetricValue"],
.stApp [data-testid="stMetricLabel"] {
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
}
.stApp code, .stApp pre, .stApp pre * {
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
}
.stApp { background: var(--paper); color: var(--ink); }
.stApp h2, .stApp h3, .stApp h4 { font-weight: 600; letter-spacing: -0.005em; }
.stApp h3 { font-size: 1.15rem; }
.stApp h4 { font-size: 1rem; }

/* Chrome */
footer, .stDeployButton { display: none !important; }
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1080px; padding-top: 2rem; padding-bottom: 3rem; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: var(--side);
  border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
.brand { display: flex; align-items: center; gap: .7rem; margin-bottom: .2rem; }
.brand-name { font-weight: 600; font-size: 1.02rem; line-height: 1.2; }
.brand-sub { color: var(--muted); font-size: .8rem; }
.side-h { font-size: .82rem; font-weight: 600; color: var(--muted); margin: .9rem 0 .35rem; }
.doc-row {
  display: flex; justify-content: space-between; gap: .6rem;
  font-size: .84rem; padding: .35rem 0; border-bottom: 1px solid var(--line);
}
.doc-row .n { color: var(--muted); white-space: nowrap; }
.doc-row .f { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-empty { font-size: .84rem; color: var(--muted); }

/* Page header */
.app-head h1 {
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
  font-size: 1.75rem; font-weight: 600; letter-spacing: -0.015em;
  margin: 0; padding: 0; color: var(--ink);
}
.app-head p { margin: .3rem 0 0; color: var(--muted); font-size: .95rem; max-width: 62ch; }

/* Status strip */
.status {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid var(--line); background: var(--surface);
  border-radius: var(--radius); margin: 1.1rem 0 1.5rem;
}
.status > div { padding: .6rem .9rem; border-left: 1px solid var(--line); min-width: 0; }
.status > div:first-child { border-left: 0; }
.status .k { font-size: .74rem; color: var(--muted); }
.status .v { font-size: .9rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.status .v.mono { font-family: 'IBM Plex Mono', monospace; font-size: .82rem; font-weight: 400; }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: .45rem; background: var(--bad); }
.ok .dot { background: var(--ok); }
@media (max-width: 760px) {
  .status { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .status > div:nth-child(3) { border-left: 0; }
  .status > div:nth-child(n+3) { border-top: 1px solid var(--line); }
}

/* Tabs */
[data-baseweb="tab-list"] { gap: 1.4rem; border-bottom: 1px solid var(--line); }
[data-baseweb="tab"] { padding: .5rem 0; height: auto; background: transparent; }
[data-baseweb="tab"] p { font-weight: 500; color: var(--muted); }
[data-baseweb="tab"][aria-selected="true"] p { color: var(--ink); }
[data-baseweb="tab-highlight"] { background: var(--accent); height: 2px; }
[data-baseweb="tab-border"] { display: none; }

/* Buttons */
.stButton > button, .stDownloadButton > button {
  border-radius: var(--radius); box-shadow: none; font-weight: 500;
  border: 1px solid var(--line-strong); background: var(--surface); color: var(--ink);
  transition: border-color .12s, color .12s, background .12s;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  border-color: var(--accent); color: var(--accent); background: var(--surface);
}
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
  background: var(--accent); border-color: var(--accent); color: var(--accent-ink);
}
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
  background: #0B4A63; border-color: #0B4A63; color: var(--accent-ink);
}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible {
  outline: 2px solid var(--accent); outline-offset: 2px;
}
.st-key-suggest .stButton > button { text-align: left; justify-content: flex-start; height: 100%; font-weight: 400; }

/* Inputs */
[data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="textarea"],
.stTextArea textarea, .stTextInput input {
  border-radius: var(--radius) !important;
  background: var(--surface) !important;
  border-color: var(--line-strong) !important;
}
[data-testid="stFileUploader"] section {
  border-radius: var(--radius); background: var(--surface); border: 1px dashed var(--line-strong);
}
[data-testid="stExpander"] {
  border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface);
}
[data-testid="stAlert"] { border-radius: var(--radius); }
[data-testid="stMetric"] {
  border: 1px solid var(--line); border-radius: var(--radius);
  background: var(--surface); padding: .7rem .9rem;
}
[data-testid="stMetricLabel"] { color: var(--muted); }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: var(--radius); }

/* Chat: ruled messages instead of bubbles */
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] { display: none; }
[data-testid="stChatMessage"] {
  background: transparent; border-radius: 0; box-shadow: none;
  border-left: 2px solid var(--accent); padding: .35rem 0 .35rem 1rem; margin-bottom: .8rem;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--surface); border: 1px solid var(--line); border-left: 2px solid var(--ink);
  padding: .6rem 1rem; border-radius: 0 var(--radius) var(--radius) 0;
}
[data-testid="stChatMessage"] pre { border: 1px solid var(--line); border-radius: var(--radius); }
[data-testid="stChatInput"] {
  border: 1px solid var(--line-strong); border-radius: var(--radius); background: var(--surface);
}
[data-testid="stChatInput"]:focus-within { border-color: var(--accent); }
.hint { font-size: .84rem; color: var(--muted); margin: .2rem 0 .8rem; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


DEFAULT_AUTOSAR_PUML = """@startuml\nskinparam rectangle {\n    BackgroundColor LightYellow\n    BorderColor Black\n}\n\ntitle AUTOSAR Basic Architecture\n\npackage \"Application Layer\" {\n    [Software Component (SWC)] as SWC <<App>>\n}\n\npackage \"Runtime Environment\" {\n    [RTE] as RTE <<RTE>>\n}\n\npackage \"Basic Software (BSW)\" {\n    [Services] as BSW_Serv <<BSW>>\n    [ECU Abstraction] as BSW_ECU <<BSW>>\n    [MCAL] as BSW_MCAL <<BSW>>\n}\n\npackage \"Microcontroller & HW\" {\n    [HW] as HW <<HW>>\n}\n\nSWC --> RTE : Ports\nRTE --> BSW_Serv : Calls\nBSW_Serv --> BSW_ECU : Uses\nBSW_ECU --> BSW_MCAL : Driver calls\nBSW_MCAL --> HW : Register access\n@enduml"""


def read_puml_template() -> str:
    """Return the PlantUML reference template, falling back to the built-in one."""
    try:
        text = PUML_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
        return text or DEFAULT_AUTOSAR_PUML
    except OSError:
        return DEFAULT_AUTOSAR_PUML


AUTOSAR_BASIC_PUML = read_puml_template()


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def init_state() -> None:
    defaults = {
        "rag_assistant": None,
        "rag_assistant_run_id": None,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    "Upload an AUTOSAR PDF from the sidebar, then ask a question. "
                    "Answers come from the indexed documentation."
                ),
            }
        ],
        PROCESSED_UPLOADS_KEY: set(),
        INDEXED_CHUNKS_KEY: [],
        "indexed_files": [],
        "pending_prompt": None,
        "custom_prompt": "",
        "llm_model": None,
        "embeddings_model": None,
        "last_error": None,
        ARCH_RESULT_KEY: None,
        "needs_reindex": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def extract_plantuml_code(response: str) -> Optional[str]:
    match = re.search(r"@startuml\b[\s\S]*?@enduml", response or "", re.IGNORECASE)
    return match.group(0) if match else None


def reset_assistant() -> None:
    st.session_state["rag_assistant"] = None
    st.session_state["rag_assistant_run_id"] = None
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "New conversation started. Indexed documents are kept.",
        }
    ]
    st.rerun()


def assistant_config_changed(llm_model: str, embeddings_model: str, custom_prompt: str) -> bool:
    return (
        st.session_state.get("llm_model") != llm_model
        or st.session_state.get("embeddings_model") != embeddings_model
        or st.session_state.get("custom_prompt") != custom_prompt
    )


def get_or_create_assistant(
    llm_model: str,
    embeddings_model: str,
    custom_prompt: str,
    openrouter_api_key: Optional[str],
):
    config_changed = assistant_config_changed(llm_model, embeddings_model, custom_prompt)
    if st.session_state["rag_assistant"] is None or config_changed:
        try:
            with st.spinner("Connecting to the model and vector store..."):
                assistant = get_rag_assistant(
                    llm_model=llm_model,
                    embeddings_model=embeddings_model,
                    instructions=custom_prompt or None,
                    openrouter_api_key=openrouter_api_key,
                )
                if st.session_state.get("needs_reindex"):
                    cached_chunks = st.session_state.get(INDEXED_CHUNKS_KEY, [])
                    if cached_chunks:
                        cached_documents = []
                        for item in cached_chunks:
                            metadata = dict(item.get("metadata", {}) or {})
                            cached_documents.append(Document(
                                content=str(item.get("content", "")),
                                name=str(metadata.get("source", "uploaded.pdf")),
                                meta_data=metadata,
                            ))
                        assistant.knowledge_base.load_documents(cached_documents, upsert=True)
                    st.session_state["needs_reindex"] = False
                run_id = assistant.create_run()

            st.session_state["rag_assistant"] = assistant
            st.session_state["rag_assistant_run_id"] = run_id
            st.session_state["llm_model"] = llm_model
            st.session_state["embeddings_model"] = embeddings_model
            st.session_state["custom_prompt"] = custom_prompt
            st.session_state["last_error"] = None
        except Exception as exc:
            st.session_state["last_error"] = str(exc)
            logger.exception("Assistant initialization failed")
            return None
    return st.session_state["rag_assistant"]


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def side_heading(text: str) -> None:
    st.markdown(f"<div class='side-h'>{html.escape(text)}</div>", unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        logo_col, name_col = st.columns([1, 3], vertical_alignment="center")
        if LOGO_PATH.exists():
            logo_col.image(str(LOGO_PATH), width=48)
        name_col.markdown(
            "<div class='brand-name'>AUTOSAR Assistant</div>"
            "<div class='brand-sub'>TATA Techpulse</div>",
            unsafe_allow_html=True,
        )

        side_heading("Models")
        llm_options = [
            "qwen2.5-coder:1.5b",
            "llama3.2:1b",
            "llama3.1",
            "llama3.2",
            "llama3",
            "phi3",
            "openrouter/free",
            "openrouter/anthropic/claude-3.5-sonnet",
            "openrouter/meta-llama/llama-3-70b-instruct",
            "openrouter/mistralai/mixtral-8x7b-instruct",
            "openhermes",
            "llama2",
            "gpt-3.5-turbo",
        ]
        llm_model = st.selectbox(
            "Language model",
            options=llm_options,
            index=0,
            help="The model that writes the answer.",
        )

        openrouter_api_key = None
        if llm_model.startswith("openrouter/"):
            openrouter_api_key = st.text_input(
                "OpenRouter API key",
                type="password",
                value=os.getenv("OPENROUTER_API_KEY", ""),
                help="Prefer setting OPENROUTER_API_KEY in your environment.",
            )
            if not openrouter_api_key:
                st.warning("Enter an OpenRouter API key to use this model.")

        embedding_options = [
            "all-minilm:l6-v2",
            "nomic-embed-text",
            "liquid/lfm-2.5-embedding-350m:free",
        ]
        embeddings_model = st.selectbox(
            "Embedding model",
            options=embedding_options,
            index=0,
            help=(
                "Changing the embedding model may need a separate Qdrant collection "
                "or a full re-index, because vector dimensions must match."
            ),
        )

        custom_prompt = st.text_area(
            "Additional instructions",
            value=st.session_state.get("custom_prompt", ""),
            placeholder="Project-specific rules, naming conventions, scope...",
            height=96,
        )

        if st.button("Apply changes", use_container_width=True):
            previous_embeddings = st.session_state.get("embeddings_model")
            cached_chunks = st.session_state.get(INDEXED_CHUNKS_KEY, [])
            st.session_state["needs_reindex"] = bool(cached_chunks) and previous_embeddings != embeddings_model
            st.session_state["rag_assistant"] = None
            st.session_state["llm_model"] = None
            st.session_state["embeddings_model"] = None
            st.session_state["custom_prompt"] = custom_prompt
            st.rerun()

        side_heading("Documents")
        uploaded_file = st.file_uploader(
            "Add AUTOSAR PDF",
            type=["pdf"],
            label_visibility="collapsed",
            help="Upload a specification or engineering document to index.",
        )

        upload_request = None
        if uploaded_file is not None:
            if st.button("Index PDF", type="primary", use_container_width=True):
                upload_request = uploaded_file

        indexed = st.session_state["indexed_files"]
        if indexed:
            rows = "".join(
                f"<div class='doc-row'><span class='f'>{html.escape(name)}</span>"
                f"<span class='n'>{count} chunks</span></div>"
                for name, count in indexed
            )
            st.markdown(rows, unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='doc-empty'>Nothing indexed in this session yet.</div>",
                unsafe_allow_html=True,
            )

        side_heading("Session")
        if st.button("New conversation", use_container_width=True):
            reset_assistant()
        if st.button("Clear indexed knowledge", use_container_width=True):
            st.session_state["confirm_clear_knowledge"] = True
        if st.session_state.get("confirm_clear_knowledge"):
            st.warning("This deletes all indexed data in the configured Qdrant collection.")
            confirm_col, cancel_col = st.columns(2)
            if confirm_col.button("Delete data", type="primary"):
                assistant = st.session_state.get("rag_assistant")
                try:
                    if assistant and assistant.knowledge_base and assistant.knowledge_base.vector_db:
                        vector_db = assistant.knowledge_base.vector_db
                        vector_db.drop()
                        # Recreate the empty collection so later indexing/search still works.
                        try:
                            vector_db.create()
                        except Exception:
                            logger.exception("Could not recreate the collection after drop")
                        st.success("Knowledge collection cleared.")
                        st.session_state[PROCESSED_UPLOADS_KEY] = set()
                        st.session_state[INDEXED_CHUNKS_KEY] = []
                        st.session_state["indexed_files"] = []
                        st.session_state[ARCH_RESULT_KEY] = None
                        st.session_state["needs_reindex"] = False
                    else:
                        st.info("Assistant or vector database is not initialized.")
                except Exception as exc:
                    st.error(f"Could not clear the collection: {exc}")
                st.session_state["confirm_clear_knowledge"] = False
            if cancel_col.button("Cancel"):
                st.session_state["confirm_clear_knowledge"] = False
                st.rerun()

    return llm_model, embeddings_model, custom_prompt, openrouter_api_key, upload_request


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def render_header(connected: bool) -> None:
    st.markdown(
        "<div class='app-head'><h1>AUTOSAR Assistant</h1>"
        "<p>Search specifications, extract component architecture, "
        "compare revisions and measure retrieval quality.</p></div>",
        unsafe_allow_html=True,
    )

    llm = st.session_state.get("llm_model") or "not set"
    emb = st.session_state.get("embeddings_model") or "not set"
    chunk_total = sum(count for _, count in st.session_state["indexed_files"])
    doc_total = len(st.session_state["indexed_files"])
    state_class = "ok" if connected else ""
    state_text = "Connected" if connected else "Not connected"

    st.markdown(
        f"""
        <div class="status">
          <div><div class="k">Language model</div><div class="v mono">{html.escape(llm)}</div></div>
          <div><div class="k">Embeddings</div><div class="v mono">{html.escape(emb)}</div></div>
          <div><div class="k">Indexed this session</div>
               <div class="v">{doc_total} document{'s' if doc_total != 1 else ''}, {chunk_total} chunks</div></div>
          <div class="{state_class}"><div class="k">Backend</div>
               <div class="v"><span class="dot"></span>{state_text}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def index_uploaded_pdf(assistant, uploaded_file) -> None:
    """Validate, index and retain source chunks for whole-document analysis."""
    if assistant is None:
        st.error("Assistant is not initialized. Check the model, API key and database connection.")
        return

    file_bytes = uploaded_file.getvalue()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        st.error(f"PDF exceeds the configured upload limit ({MAX_UPLOAD_BYTES // (1024 * 1024)} MiB).")
        return
    if not file_bytes.startswith(b"%PDF-"):
        st.error("The upload does not have a valid PDF signature.")
        return

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    if file_hash in st.session_state[PROCESSED_UPLOADS_KEY]:
        st.info("This exact PDF was already indexed in this session.")
        return

    project_id = os.getenv("AUTOSAR_PROJECT_ID", "local")
    try:
        with st.status(f"Indexing {uploaded_file.name}", expanded=True) as status:
            st.write("Reading PDF pages...")
            loader = AutosarLoader(
                uploaded_file,
                document_version=file_hash[:12],
                project_id=project_id,
            )
            raw_documents = loader.load()
            if not raw_documents:
                status.update(label="PDF could not be read", state="error")
                st.error("No pages could be extracted from the PDF.")
                return

            failed_pages = [
                doc.metadata.get("page_number")
                for doc in raw_documents
                if not doc.page_content.strip()
            ]
            st.write(f"Read {len(raw_documents)} pages; {len(failed_pages)} page(s) have no usable extracted text.")
            if failed_pages:
                st.warning(
                    "Pages without extractable text: " + ", ".join(map(str, failed_pages))
                    + ". OCR may be unavailable or those pages may require manual review."
                )

            st.write("Splitting text into retrieval chunks...")
            splitter = AutosarSplitter(chunk_size=1200, chunk_overlap=200)
            chunks = splitter.split_documents(raw_documents)
            chunks = remove_empty_documents(chunks)
            if not chunks:
                status.update(label="No usable text chunks found", state="error")
                st.error("No non-empty text chunks found. Check PDF extraction before indexing.")
                return

            phi_documents = []
            for chunk in chunks:
                clean_text = chunk.page_content.strip()
                if not clean_text:
                    continue
                metadata = dict(getattr(chunk, "metadata", {}) or {})
                metadata["source_sha256"] = file_hash
                metadata["project_id"] = project_id
                source = metadata.get("source", uploaded_file.name)
                phi_documents.append(Document(content=clean_text, name=str(source), meta_data=metadata))

            if not phi_documents:
                status.update(label="No non-empty chunks to index", state="error")
                st.error("All chunks were empty after sanitization. Check PDF extraction before indexing.")
                return

            st.write(f"Writing {len(phi_documents)} chunks to the vector database...")
            assistant.knowledge_base.load_documents(phi_documents, upsert=True)

            # Cache the exact chunk corpus for whole-document extraction. A top-k
            # semantic query is not a substitute for exhaustive architecture extraction.
            st.session_state[INDEXED_CHUNKS_KEY].extend(
                {"content": chunk.page_content, "metadata": dict(chunk.metadata or {})}
                for chunk in chunks
            )
            st.session_state[PROCESSED_UPLOADS_KEY].add(file_hash)
            st.session_state["indexed_files"].append((uploaded_file.name, len(phi_documents)))
            status.update(label=f"Indexed {uploaded_file.name}", state="complete")
    except Exception as exc:
        logger.exception("PDF indexing failed")
        st.error(f"Indexing failed: {exc}")
        st.caption(
            "Check database connectivity, OCR availability and embedding dimensions. "
            "Do not ignore vector-dimension errors; the target collection must match the selected embedder."
        )
        return

    st.rerun()


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

DIAGRAM_FLAG = re.compile(r"(?<!\S)/bd\b")


def build_query(prompt: str) -> tuple[str, bool]:
    is_diagram_request = bool(DIAGRAM_FLAG.search(prompt))
    if not is_diagram_request:
        return prompt, False

    query = DIAGRAM_FLAG.sub("", prompt).strip()
    if AUTOSAR_BASIC_PUML:
        query += (
            "\nGenerate a PlantUML block diagram. Return the code between "
            "@startuml and @enduml, using this architecture as a reference:\n"
            + AUTOSAR_BASIC_PUML
        )
    else:
        query += "\nGenerate a PlantUML block diagram between @startuml and @enduml."
    return query, True


def queue_prompt(text: str) -> None:
    st.session_state["pending_prompt"] = text


def _document_metadata(document) -> dict:
    metadata = getattr(document, "meta_data", None) or getattr(document, "metadata", None) or {}
    return metadata if isinstance(metadata, dict) else {}


def render_retrieved_sources(assistant, query: str) -> None:
    """Display source candidates with provenance; do not call them verified citations."""
    try:
        retrieved = assistant.knowledge_base.search(query) or []
    except Exception as exc:
        logger.warning("Could not render retrieved sources: %s", exc)
        st.caption("Source candidates could not be displayed for this answer.")
        return
    if not retrieved:
        st.caption("No source candidates were returned for the query.")
        return
    with st.expander("Retrieved source passages to verify", expanded=False):
        for index, doc in enumerate(retrieved[:12], start=1):
            metadata = _document_metadata(doc)
            name = metadata.get("source") or getattr(doc, "name", None) or "Unknown source"
            page = metadata.get("page_number") or metadata.get("page_start")
            section = metadata.get("section_path") or metadata.get("section_headings") or []
            if isinstance(section, list):
                section_text = " / ".join(str(item) for item in section if item)
            else:
                section_text = str(section or "")
            header = f"{index}. {name}" + (f" · page {page}" if page is not None else "")
            if section_text:
                header += f" · {section_text}"
            st.markdown(f"**{header}**")
            content = getattr(doc, "content", None) or getattr(doc, "page_content", None) or ""
            if content:
                snippet = str(content).strip()
                st.text(snippet[:900] + ("…" if len(snippet) > 900 else ""))
            if metadata.get("chunk_id"):
                st.caption(f"Chunk ID: {metadata['chunk_id']}")
        st.caption("These are retrieved source candidates. Verify that each passage supports the claim before using it as an engineering finding.")


def render_chat(assistant) -> None:
    pending = st.session_state.pop("pending_prompt", None)

    for message in st.session_state["messages"]:
        if message.get("role") not in {"assistant", "user"}:
            continue
        with st.chat_message(message["role"]):
            st.markdown(message.get("content", ""))

    if len(st.session_state["messages"]) == 1 and not pending:
        st.markdown(
            "<div class='hint'>Try one of these, or type your own. "
            "Add <code>/bd</code> to a question to get a block diagram.</div>",
            unsafe_allow_html=True,
        )
        # A keyed container gets the CSS class "st-key-suggest" (Streamlit >= 1.39).
        with st.container(key="suggest"):
            cols = st.columns(len(SUGGESTED_QUESTIONS))
            for idx, (col, text) in enumerate(zip(cols, SUGGESTED_QUESTIONS)):
                col.button(
                    text,
                    key=f"suggest_{idx}",
                    on_click=queue_prompt,
                    args=(text,),
                    use_container_width=True,
                )

    typed = st.chat_input("Ask about your AUTOSAR documents")
    prompt = typed or pending
    if not prompt:
        return

    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if assistant is None:
        with st.chat_message("assistant"):
            st.error("The assistant is unavailable. Fix the configuration or database connection first.")
        return

    query, is_diagram_request = build_query(prompt)

    with st.chat_message("assistant"):
        response_area = st.empty()
        full_response = ""
        try:
            with st.spinner("Searching indexed documents..."):
                result = assistant.run(query)
                if isinstance(result, str):
                    full_response = result
                elif hasattr(result, "content") and isinstance(result.content, str):
                    full_response = result.content
                else:
                    for delta in result:
                        if isinstance(delta, str):
                            full_response += delta
                        elif getattr(delta, "content", None):
                            full_response += str(delta.content)
                        response_area.markdown(full_response)
            response_area.markdown(full_response or "_No response returned._")
            if full_response.strip():
                st.caption(
                    "Model-generated citations and retrieved passages are evidence candidates, not an engineering approval. "
                    "Open the source passages below and verify that they support each material claim."
                )
            st.session_state["messages"].append(
                {"role": "assistant", "content": full_response or "No response returned."}
            )
            render_retrieved_sources(assistant, query)

            if is_diagram_request:
                render_diagram(full_response)
        except Exception as exc:
            logger.exception("Chat response failed")
            response_area.error(f"Could not generate a response: {exc}")


def render_diagram(full_response: str) -> None:
    puml_code = extract_plantuml_code(full_response)
    if not puml_code:
        st.info("No PlantUML block was found in the response. Ask for code between @startuml and @enduml.")
        return

    puml_path = BASE_DIR / "generated_diagram.puml"
    image_path = BASE_DIR / "output.png"
    puml_path.write_text(puml_code, encoding="utf-8")
    try:
        generate_plantuml_image(str(puml_path), str(image_path))
        if image_path.exists():
            st.image(str(image_path), caption="Generated block diagram", use_container_width=True)
            st.download_button(
                "Download PlantUML source",
                data=puml_code,
                file_name="generated_diagram.puml",
                mime="text/plain",
            )
    except Exception as exc:
        st.warning(f"Diagram rendering failed. The PlantUML source is shown below. ({exc})")
        st.code(puml_code, language="text")


# ---------------------------------------------------------------------------
# Architecture analysis
# ---------------------------------------------------------------------------

def _puml_alias(text: str, used: set[str], prefix: str = "n") -> str:
    """Make a unique PlantUML-safe identifier from arbitrary text."""
    base = re.sub(r"\W+", "_", str(text)).strip("_") or prefix
    if base[0].isdigit():
        base = f"{prefix}_{base}"
    alias, n = base, 2
    while alias in used:
        alias = f"{base}_{n}"
        n += 1
    used.add(alias)
    return alias


def _puml_label(text: str) -> str:
    return str(text).replace('"', "'").replace("\n", " ")


def build_component_puml(model_or_components) -> str:
    """Build a conservative diagram from extracted entities and explicit edges."""
    if isinstance(model_or_components, dict):
        model = model_or_components
        components = model.get("components", []) or []
        interfaces = model.get("interfaces", []) or []
        dependencies = model.get("dependencies", []) or []
    else:
        model = {"components": model_or_components or [], "interfaces": [], "dependencies": []}
        components = model["components"]
        interfaces = []
        dependencies = []

    lines = [
        "@startuml",
        "skinparam component {",
        "    BackgroundColor LightYellow",
        "    BorderColor Black",
        "}",
        "title Extracted AUTOSAR architecture (evidence-derived relationships only)",
    ]
    used: set[str] = set()
    component_aliases: dict[str, str] = {}
    interface_aliases: dict[str, str] = {}
    port_links: list[tuple[str, str, str]] = []

    for comp in components:
        if not isinstance(comp, dict) or not comp.get("name"):
            continue
        comp_name = str(comp["name"])
        comp_alias = _puml_alias(comp_name, used, "comp")
        component_aliases[" ".join(comp_name.casefold().split())] = comp_alias
        lines.append(f'component "{_puml_label(comp_name)}" as {comp_alias}')
        for port in comp.get("ports", []) or []:
            if not isinstance(port, dict):
                continue
            port_name = str(port.get("name", "port"))
            port_alias = _puml_alias(f"{comp_alias}_{port_name}", used, "port")
            direction = port.get("direction", "unknown")
            interface_name = port.get("interface_name", port.get("interface"))
            description = str(interface_name or direction or "")
            suffix = f" : {_puml_label(description)}" if description else ""
            lines.append(f'() "{_puml_label(port_name)}" as {port_alias}')
            lines.append(f"{comp_alias} -- {port_alias}{suffix}")
            if interface_name:
                port_links.append((port_alias, str(interface_name), port_name))

    for interface in interfaces:
        if not isinstance(interface, dict) or not interface.get("name"):
            continue
        name = str(interface["name"])
        alias = _puml_alias(name, used, "if")
        interface_aliases[" ".join(name.casefold().split())] = alias
        lines.append(f'interface "{_puml_label(name)}" as {alias}')

    for port_alias, interface_name, port_name in port_links:
        target = interface_aliases.get(" ".join(interface_name.casefold().split()))
        if target:
            lines.append(f'{port_alias} ..> {target} : {_puml_label(port_name)}')

    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        source = dependency.get("source_entity", dependency.get("source"))
        target = dependency.get("target_entity", dependency.get("target"))
        if not source or not target:
            continue
        source_key = " ".join(str(source).casefold().split())
        target_key = " ".join(str(target).casefold().split())
        source_alias = component_aliases.get(source_key) or interface_aliases.get(source_key)
        target_alias = component_aliases.get(target_key) or interface_aliases.get(target_key)
        if source_alias and target_alias:
            relationship = _puml_label(str(dependency.get("relationship", "depends on")))
            lines.append(f"{source_alias} --> {target_alias} : {relationship}")

    lines.append("note bottom : Relationships are rendered only when extracted explicitly. Review source evidence before engineering use.")
    lines.append("@enduml")
    return "\n".join(lines)


def render_component_diagram(model_or_components) -> None:
    puml_code = build_component_puml(model_or_components)
    puml_path = BASE_DIR / "generated_component_diagram.puml"
    image_path = BASE_DIR / "component_diagram.png"
    puml_path.write_text(puml_code, encoding="utf-8")
    try:
        generate_plantuml_image(str(puml_path), str(image_path))
        if image_path.exists():
            st.image(str(image_path), caption="Evidence-derived component diagram", use_container_width=True)
            st.download_button(
                "Download PlantUML",
                data=puml_code,
                file_name="component_diagram.puml",
                mime="text/plain",
                key="dl_component_puml",
            )
    except Exception as exc:
        st.warning(f"Diagram rendering failed: {exc}")
        st.code(puml_code, language="text")


def run_extraction(assistant, llm_model: str, api_key: Optional[str]) -> Optional[dict]:
    """Extract architecture from every source chunk indexed in this session."""
    source_chunks = st.session_state.get(INDEXED_CHUNKS_KEY, [])
    if not source_chunks:
        st.warning(
            "No source chunks are cached for whole-document extraction. Re-index the PDF in this session; "
            "a top-k semantic search cannot establish extraction completeness."
        )
        return None

    extractor = StructuredExtractor(llm_model=llm_model, openrouter_api_key=api_key)
    extractions = []
    failures = []
    progress = st.progress(0.0, text="Extracting architecture entities from indexed chunks...")
    total = len(source_chunks)
    for index, item in enumerate(source_chunks, start=1):
        text = str(item.get("content", "") or "")
        metadata = dict(item.get("metadata", {}) or {})
        if text.strip():
            try:
                extractions.append(extractor.extract_from_text(text, source_metadata=metadata))
            except Exception as exc:
                logger.exception("Architecture extraction failed for chunk %s", metadata.get("chunk_id", index))
                failures.append({
                    "chunk_id": metadata.get("chunk_id"),
                    "source": metadata.get("source"),
                    "page_number": metadata.get("page_number"),
                    "error": f"{type(exc).__name__}: {exc}",
                })
        progress.progress(index / total, text=f"Processed {index}/{total} chunks")
    progress.empty()

    model = extractor.merge_extractions(extractions)
    findings = ConsistencyValidator().validate_model(model)
    return {
        "model": model,
        "findings": findings,
        "extraction_stats": {
            "total_chunks": total,
            "successful_chunks": len(extractions),
            "failed_chunks": len(failures),
            "failure_details": failures[:25],
            "source_documents": sorted({str(item.get("metadata", {}).get("source", "unknown")) for item in source_chunks}),
        },
    }


def extract_architecture_from_pdf(uploaded_file, llm_model: str, api_key: Optional[str]) -> dict:
    """Create a temporary evidence-backed model directly from an uploaded PDF."""
    file_bytes = uploaded_file.getvalue()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError(f"PDF exceeds the configured upload limit of {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB.")
    if not file_bytes.startswith(b"%PDF-"):
        raise ValueError("Uploaded revision is not a valid PDF file.")

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    project_id = os.getenv("AUTOSAR_PROJECT_ID", "revision-review")
    loader = AutosarLoader(uploaded_file, document_version=file_hash[:12], project_id=project_id)
    pages = loader.load()
    chunks = AutosarSplitter(chunk_size=1200, chunk_overlap=200).split_documents(pages)
    if not chunks:
        raise ValueError("No non-empty text chunks could be extracted from this revision.")

    extractor = StructuredExtractor(llm_model=llm_model, openrouter_api_key=api_key)
    extractions = []
    failures = []
    progress = st.progress(0.0, text=f"Extracting {uploaded_file.name}...")
    for index, chunk in enumerate(chunks, start=1):
        try:
            extractions.append(extractor.extract_from_text(chunk.page_content, source_metadata=chunk.metadata))
        except Exception as exc:
            failures.append({"chunk_id": chunk.metadata.get("chunk_id"), "page_number": chunk.metadata.get("page_number"), "error": f"{type(exc).__name__}: {exc}"})
        progress.progress(index / len(chunks), text=f"{uploaded_file.name}: {index}/{len(chunks)} chunks")
    progress.empty()
    if not extractions:
        raise RuntimeError(f"Extraction failed for every chunk in {uploaded_file.name}; compare aborted.")
    model = extractor.merge_extractions(extractions)
    return {
        "model": model,
        "stats": {"pages": len(pages), "chunks": len(chunks), "successful_chunks": len(extractions), "failed_chunks": len(failures), "failures": failures[:25]},
    }


def render_structured_analysis(assistant, llm_model: str, api_key: Optional[str]) -> None:
    st.markdown("#### Architecture extraction")
    st.write(
        "Extracts architecture from every chunk retained for indexed documents in this session. "
        "Extraction failures and source evidence are retained for review; this is not a compliance approval."
    )

    if st.button("Run extraction", type="primary"):
        if assistant is None or not getattr(assistant, "knowledge_base", None):
            st.warning("Initialize the assistant and index a PDF first.")
        else:
            try:
                with st.spinner("Retrieving evidence and extracting components..."):
                    st.session_state[ARCH_RESULT_KEY] = run_extraction(assistant, llm_model, api_key)
            except Exception as exc:
                logger.exception("Structured analysis failed")
                st.error(f"Structured analysis failed: {exc}")

    # Results live in session_state so they survive the reruns caused by
    # the download and diagram buttons below.
    result = st.session_state.get(ARCH_RESULT_KEY)
    if not result:
        return

    model = result["model"]
    findings = result["findings"]
    stats = result.get("extraction_stats", {})
    if stats:
        a, b, c = st.columns(3)
        a.metric("Chunks processed", stats.get("total_chunks", 0))
        b.metric("Successful extractions", stats.get("successful_chunks", 0))
        c.metric("Failed extractions", stats.get("failed_chunks", 0))
        if stats.get("failure_details"):
            with st.expander("Extraction failures", expanded=False):
                st.dataframe(pd.DataFrame(stats["failure_details"]), use_container_width=True, hide_index=True)
    components = model.get("components", []) or []
    total_ports = sum(len(item.get("ports", []) or []) for item in components)

    m1, m2, m3 = st.columns(3)
    m1.metric("Components", len(components))
    m2.metric("Ports", total_ports)
    m3.metric("Findings", len(findings))

    if components:
        df = pd.DataFrame(
            [
                {
                    "Component": item.get("name", "Unknown"),
                    "Type": item.get("component_type", item.get("type", "N/A")) or "N/A",
                    "Ports": len(item.get("ports", []) or []),
                }
                for item in components
            ]
        )
        st.markdown("#### Component inventory")
        st.dataframe(df, use_container_width=True, hide_index=True)
        left, right = st.columns(2)
        left.download_button(
            "Download JSON",
            data=json.dumps(model, indent=2, ensure_ascii=False),
            file_name="architecture_inventory.json",
            mime="application/json",
            use_container_width=True,
        )
        right.download_button(
            "Download CSV",
            data=df.to_csv(index=False),
            file_name="components_inventory.csv",
            mime="text/csv",
            use_container_width=True,
        )
        if st.button("Generate component diagram", key="gen_component_diagram"):
            render_component_diagram(model)
    else:
        st.info("No components were extracted from the retrieved evidence.")

    for section_key, title, columns in [
        ("interfaces", "Interface inventory", ["name", "interface_type", "signals"]),
        ("signals", "Signal inventory", ["name", "data_type", "unit"]),
        ("functional_flows", "Functional flows", ["name", "steps"]),
        ("dependencies", "Dependencies", ["source_entity", "relationship", "target_entity", "description"]),
    ]:
        records = model.get(section_key, []) or []
        st.markdown(f"#### {title}")
        if records:
            st.dataframe(pd.DataFrame([{col: item.get(col) for col in columns} for item in records]), use_container_width=True, hide_index=True)
        else:
            st.caption(f"No {title.casefold()} were extracted. This may mean the source does not define them or extraction did not identify them.")

    st.markdown("#### Consistency report")
    if findings:
        for finding in findings:
            severity = str(finding.get("severity", "Warning")).lower()
            message = (
                f"**{finding.get('component', 'Unknown component')}**: "
                f"{finding.get('issue', 'Unspecified finding')}"
            )
            if severity == "error":
                st.error(message)
            else:
                st.warning(message)
            evidence = finding.get("evidence", []) or []
            if evidence:
                source_labels = [
                    f"{item.get('source', 'source')} · page {item.get('page_number', '?')}"
                    for item in evidence if isinstance(item, dict)
                ]
                if source_labels:
                    st.caption("Evidence: " + "; ".join(source_labels))
    else:
        if stats.get("failed_chunks", 0):
            st.warning("No consistency findings were generated, but extraction was incomplete. This is not evidence that the model is complete or consistent.")
        else:
            st.success("No issues were found in the extracted fields. This is not a formal AUTOSAR compliance approval.")


# ---------------------------------------------------------------------------
# Revision comparison
# ---------------------------------------------------------------------------

def _load_revision_architecture(uploaded_file, llm_model: str, api_key: Optional[str]) -> tuple[dict, dict]:
    suffix = Path(getattr(uploaded_file, "name", "")).suffix.casefold()
    if suffix == ".json":
        raw = json.loads(uploaded_file.getvalue().decode("utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("components", []), list):
            raise ValueError("JSON revision must be an architecture object with a components list.")
        return raw, {"source_type": "json", "name": uploaded_file.name}
    if suffix == ".pdf":
        result = extract_architecture_from_pdf(uploaded_file, llm_model, api_key)
        return result["model"], {"source_type": "pdf", "name": uploaded_file.name, **result["stats"]}
    raise ValueError("Revision file must be a PDF or a JSON architecture inventory.")


def render_revision_comparison(llm_model: str, api_key: Optional[str]) -> None:
    st.markdown("#### Compare architecture revisions")
    st.write(
        "Upload two PDF revisions to extract and compare their architecture models, "
        "or upload existing JSON inventories. PDF comparison invokes the selected LLM per chunk. "
        "Treat detected changes as review candidates, not approved engineering decisions."
    )
    col_old, col_new = st.columns(2)
    with col_old:
        old_file = st.file_uploader("Older revision (PDF or JSON)", type=["pdf", "json"], key="old_revision_file")
    with col_new:
        new_file = st.file_uploader("Newer revision (PDF or JSON)", type=["pdf", "json"], key="new_revision_file")

    if not (old_file and new_file):
        return
    if not st.button("Extract and compare revisions", type="primary"):
        return

    try:
        with st.spinner("Preparing old and new architecture models..."):
            old_model, old_meta = _load_revision_architecture(old_file, llm_model, api_key)
            new_model, new_meta = _load_revision_architecture(new_file, llm_model, api_key)
        diff = ConsistencyValidator().compare_revisions(old_model, new_model)
        a, r, m = st.columns(3)
        a.metric("Components added", len(diff.get("added_components", [])))
        r.metric("Components removed", len(diff.get("removed_components", [])))
        m.metric("Components modified", len(diff.get("modified_components", [])))

        for key, title in [
            ("added_components", "Added components"),
            ("removed_components", "Removed components"),
            ("modified_components", "Modified components"),
            ("added_interfaces", "Added interfaces"),
            ("removed_interfaces", "Removed interfaces"),
            ("modified_interfaces", "Modified interfaces"),
            ("added_signals", "Added signals"),
            ("removed_signals", "Removed signals"),
            ("modified_signals", "Modified signals"),
            ("added_functional_flows", "Added functional flows"),
            ("removed_functional_flows", "Removed functional flows"),
            ("modified_functional_flows", "Modified functional flows"),
            ("added_dependencies", "Added dependencies"),
            ("removed_dependencies", "Removed dependencies"),
        ]:
            values = diff.get(key, [])
            if values:
                st.markdown(f"**{title}:** " + ", ".join(map(str, values)))

        changes = diff.get("changes", [])
        if changes:
            st.markdown("#### Field-level changes")
            rows = []
            for change in changes:
                def label_evidence(value):
                    labels = []
                    for evidence in value or []:
                        if isinstance(evidence, dict):
                            name = evidence.get("source", "source")
                            page = evidence.get("page_number", "?")
                            labels.append(f"{name}, p. {page}")
                    return "; ".join(labels)
                rows.append({
                    "Entity type": change.get("entity_type", "entity"),
                    "Entity": change.get("entity", ""),
                    "Change": change.get("change_type", "modified"),
                    "Path": change.get("path", ""),
                    "Old value": json.dumps(change.get("old"), ensure_ascii=False),
                    "New value": json.dumps(change.get("new"), ensure_ascii=False),
                    "Old evidence": label_evidence(change.get("old_evidence")),
                    "New evidence": label_evidence(change.get("new_evidence")),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.download_button(
                "Download revision diff JSON",
                data=json.dumps(diff, indent=2, ensure_ascii=False),
                file_name="architecture_revision_diff.json",
                mime="application/json",
            )
        elif not any(diff.get(key) for key in ("added_components", "removed_components", "modified_components", "added_interfaces", "removed_interfaces", "modified_interfaces", "added_signals", "removed_signals", "modified_signals", "added_dependencies", "removed_dependencies")):
            st.info("No model changes were detected. Extraction completeness must still be reviewed.")

        with st.expander("Revision extraction summary", expanded=False):
            st.json({"older_revision": old_meta, "newer_revision": new_meta})
    except Exception as exc:
        logger.exception("Revision comparison failed")
        st.error(f"Could not compare revisions: {exc}")


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def render_dataset_evaluation() -> None:
    st.markdown("#### Retrieval evaluation")
    st.write("Run the evaluation module against your test dataset and download its report.")
    try:
        import evaluate_dataset
    except Exception as exc:
        st.error(f"Could not import evaluate_dataset.py: {exc}")
        st.caption("Place evaluate_dataset.py next to app.py and check its dependencies.")
        return

    mode = st.radio("Mode", ["Single question", "Batch"], horizontal=True)
    if mode == "Single question":
        question_id = st.text_input("Question ID", placeholder="LDCOM-005")
        if st.button("Run evaluation", type="primary"):
            if not question_id.strip():
                st.warning("Enter a question ID.")
                return
            try:
                with st.spinner(f"Evaluating {question_id.strip()}..."):
                    result = evaluate_dataset.answer_single_question(question_id.strip())
                if result is not None:
                    st.write(result)
                else:
                    st.success("Evaluation finished. Check the module's configured output.")
            except Exception as exc:
                st.error(f"Evaluation failed: {exc}")
    else:
        limit = st.number_input(
            "Number of questions (0 runs the complete benchmark)",
            min_value=0,
            max_value=10000,
            value=0,
            step=1,
        )
        if st.button("Run batch", type="primary"):
            try:
                with st.spinner("Running evaluation..."):
                    if limit > 0:
                        result = evaluate_dataset.answer_dataset(limit=int(limit))
                    else:
                        result = evaluate_dataset.answer_dataset()
                if result is not None:
                    st.write(result)
                st.success("Batch evaluation finished.")
                for attr, label in [
                    ("OUTPUT_JSON", "Download JSON results"),
                    ("OUTPUT_REPORT", "Download Markdown report"),
                ]:
                    path = getattr(evaluate_dataset, attr, None)
                    if path and os.path.exists(path):
                        with open(path, "rb") as handle:
                            st.download_button(
                                label,
                                data=handle.read(),
                                file_name=os.path.basename(path),
                                key=f"dl_{attr}",
                            )
            except Exception as exc:
                st.error(f"Batch evaluation failed: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    init_state()
    inject_css()

    llm_model, embeddings_model, custom_prompt, api_key, upload_request = render_sidebar()

    assistant = get_or_create_assistant(
        llm_model=llm_model,
        embeddings_model=embeddings_model,
        custom_prompt=custom_prompt,
        openrouter_api_key=api_key,
    )

    if upload_request is not None:
        index_uploaded_pdf(assistant, upload_request)

    render_header(connected=assistant is not None)

    if st.session_state.get("last_error"):
        st.error(f"Assistant initialization failed: {st.session_state['last_error']}")
        st.caption("Check that Ollama, Qdrant and PostgreSQL are running and the selected model is available.")

    tab_chat, tab_architecture, tab_revisions, tab_evaluation = st.tabs(
        ["Chat", "Architecture", "Revisions", "Evaluation"]
    )

    with tab_chat:
        render_chat(assistant)

    with tab_architecture:
        render_structured_analysis(assistant, llm_model, api_key)

    with tab_revisions:
        render_revision_comparison(llm_model, api_key)

    with tab_evaluation:
        render_dataset_evaluation()


if __name__ == "__main__":
    main()