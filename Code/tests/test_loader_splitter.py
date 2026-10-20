from pathlib import Path
import pytest


@pytest.fixture
def langchain_modules():
    """Use real LangChain when installed; otherwise skip these integration tests."""
    pytest.importorskip("langchain_core")
    pytest.importorskip("langchain_text_splitters")


def test_bundled_pdf_extracts_page_provenance(langchain_modules):
    from autosar_rag.autosar_loader import AutosarLoader

    project_root = Path(__file__).resolve().parents[1]
    pdf_path = project_root / "assets" / "doc" / "AUTOSAR_SWS_LargeDataCOM.pdf"
    if not pdf_path.exists():
        pytest.skip("Bundled reference PDF is unavailable in this source distribution.")
    pages = AutosarLoader(pdf_path, enable_ocr=False, project_id="test-project").load()
    assert len(pages) > 0
    assert all("page_number" in page.metadata for page in pages)
    assert all(page.metadata.get("source_sha256") for page in pages)
    assert all(page.metadata.get("document_id") for page in pages)
    assert [page.metadata["page_number"] for page in pages] == list(range(1, len(pages) + 1))
    assert any(page.page_content.strip() for page in pages)


def test_splitter_preserves_metadata_and_reproducible_chunk_ids(langchain_modules):
    from langchain_core.documents import Document
    from autosar_rag.autosar_splitter import AutosarSplitter

    source = Document(
        page_content=("API definition and parameter details. " * 100),
        metadata={"source": "example.pdf", "document_id": "doc-hash", "page_number": 7, "project_id": "test"},
    )
    splitter = AutosarSplitter(chunk_size=300, chunk_overlap=50)
    first = splitter.split_documents([source])
    second = splitter.split_documents([source])
    assert len(first) > 1
    assert [doc.metadata["chunk_id"] for doc in first] == [doc.metadata["chunk_id"] for doc in second]
    assert all(doc.metadata["page_number"] == 7 for doc in first)
    assert all(doc.metadata["project_id"] == "test" for doc in first)
    assert all(doc.metadata["chunk_end_char"] - doc.metadata["chunk_start_char"] == len(doc.page_content) for doc in first)


def test_remove_empty_documents(langchain_modules):
    from langchain_core.documents import Document
    from autosar_rag.autosar_splitter import remove_empty_documents, AutosarSplitter

    valid_doc = Document(page_content="Valid technical content for AUTOSAR SWS.", metadata={"page": 1})
    empty_doc = Document(page_content="", metadata={"page": 2})
    whitespace_doc = Document(page_content="   \n\t  \n  ", metadata={"page": 3})

    filtered = remove_empty_documents([valid_doc, empty_doc, whitespace_doc])
    assert len(filtered) == 1
    assert filtered[0].page_content == "Valid technical content for AUTOSAR SWS."

    splitter = AutosarSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents([valid_doc, empty_doc, whitespace_doc])
    assert len(chunks) >= 1
    assert all(len(c.page_content.strip()) > 0 for c in chunks)


def test_validate_embedding():
    import pytest
    pytest.importorskip("phi")
    from assistant.assistant import validate_embedding

    valid_vec = [0.1, 0.2, 0.3, 0.4]
    result = validate_embedding("test query", valid_vec, expected_dimension=4)
    assert result == valid_vec

    with pytest.raises(ValueError, match="Cannot embed empty text"):
        validate_embedding("", valid_vec)

    with pytest.raises(ValueError, match="empty vector"):
        validate_embedding("test query", [])

    with pytest.raises(ValueError, match="Expected 4 dimensions, received 3"):
        validate_embedding("test query", [0.1, 0.2, 0.3], expected_dimension=4)

    with pytest.raises(ValueError, match="NaN or infinity"):
        validate_embedding("test query", [0.1, float("nan"), 0.3, 0.4])
