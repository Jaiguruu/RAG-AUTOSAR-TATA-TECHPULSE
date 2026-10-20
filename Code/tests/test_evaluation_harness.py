from pathlib import Path

from evaluate_dataset import _capture_retrieval_trace, evaluation_collection_name


class FakeDocument:
    name = "source.pdf"
    content = "API documentation text"
    meta_data = {
        "source": "source.pdf",
        "document_id": "doc-1",
        "document_version": "v1",
        "page_number": 7,
        "section_path": ["Module", "API"],
        "chunk_id": "chunk-1",
        "source_sha256": "abc123",
    }


class FakeKnowledgeBase:
    def search(self, query):
        assert query == "Where is the API documented?"
        return [FakeDocument()]


class FakeAssistant:
    knowledge_base = FakeKnowledgeBase()


def test_collection_name_changes_when_pdf_or_dataset_changes(tmp_path):
    pdf = tmp_path / "source.pdf"
    dataset = tmp_path / "dataset.json"
    pdf.write_bytes(b"pdf-1")
    dataset.write_text("[]", encoding="utf-8")
    first = evaluation_collection_name(pdf, dataset, "embed-model")
    pdf.write_bytes(b"pdf-2")
    second = evaluation_collection_name(pdf, dataset, "embed-model")
    assert first != second


def test_retrieval_trace_preserves_provenance_and_snippet():
    result = _capture_retrieval_trace(FakeAssistant(), "Where is the API documented?")
    assert result["status"] == "captured"
    candidate = result["candidates"][0]
    assert candidate["source"] == "source.pdf"
    assert candidate["page_number"] == 7
    assert candidate["chunk_id"] == "chunk-1"
    assert candidate["snippet"] == "API documentation text"


def test_retrieval_trace_failure_does_not_hide_error():
    class BrokenKnowledgeBase:
        def search(self, query):
            raise RuntimeError("vector store unavailable")

    class BrokenAssistant:
        knowledge_base = BrokenKnowledgeBase()

    result = _capture_retrieval_trace(BrokenAssistant(), "question")
    assert result["status"] == "retrieval_trace_failed"
    assert "vector store unavailable" in result["error"]
    assert result["candidates"] == []


def test_reset_evaluation_collection_refuses_shared_user_collection():
    from evaluate_dataset import _reset_evaluation_collection

    class Client:
        def delete_collection(self, collection_name):
            raise AssertionError("shared collection must never be deleted")

    class VectorDB:
        collection = "autosar_rag_local_model"
        client = Client()

        def create(self):
            raise AssertionError("shared collection must never be recreated")

    class KnowledgeBase:
        vector_db = VectorDB()

    class Assistant:
        knowledge_base = KnowledgeBase()

    try:
        _reset_evaluation_collection(Assistant())
    except RuntimeError as exc:
        assert "Refusing to reset a non-evaluation" in str(exc)
    else:
        raise AssertionError("Expected guard against deleting non-evaluation collection")


def test_reset_evaluation_collection_recreates_only_evaluation_collection():
    from evaluate_dataset import _reset_evaluation_collection

    events = []

    class Client:
        def delete_collection(self, collection_name):
            events.append(("delete", collection_name))

    class VectorDB:
        collection = "autosar_eval_pdf_dataset_embed"
        client = Client()

        def create(self):
            events.append(("create", self.collection))

    class KnowledgeBase:
        vector_db = VectorDB()

    class Assistant:
        knowledge_base = KnowledgeBase()

    _reset_evaluation_collection(Assistant())
    assert events == [
        ("delete", "autosar_eval_pdf_dataset_embed"),
        ("create", "autosar_eval_pdf_dataset_embed"),
    ]


def test_reference_dataset_contains_expected_full_benchmark():
    import json
    from evaluate_dataset import DEFAULT_DATASET

    dataset = json.loads(DEFAULT_DATASET.read_text(encoding="utf-8"))
    assert len(dataset) == 24
    assert len({str(item["id"]) for item in dataset}) == 24
