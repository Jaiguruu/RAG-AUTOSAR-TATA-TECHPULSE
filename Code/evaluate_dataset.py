"""Evaluate AUTOSAR Q&A against an isolated, reproducible source corpus.

The score reported here is keyword coverage, not factual accuracy. The benchmark
corpus is rebuilt before each run so persistent vectors from ordinary uploads
cannot contaminate the results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from autosar_rag.evaluation_metrics import check_must_include

WORKSPACE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = WORKSPACE_DIR / "autosar_large_data_com_test_dataset.json"
PDF_PATH = WORKSPACE_DIR / "assets" / "doc" / "AUTOSAR_SWS_LargeDataCOM.pdf"
OUTPUT_JSON = WORKSPACE_DIR / "autosar_large_data_com_answers.json"
OUTPUT_REPORT = WORKSPACE_DIR / "evaluation_report.md"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _collection_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")[:24] or "default"


def evaluation_collection_name(pdf_path: Path, dataset_path: Path, embeddings_model: str) -> str:
    """Stable isolated namespace bound to exact source, dataset and embedder."""
    source_hash = sha256_file(pdf_path)
    dataset_hash = sha256_file(dataset_path)
    embed_hash = hashlib.sha256(embeddings_model.encode("utf-8")).hexdigest()[:8]
    return f"autosar_eval_{source_hash[:10]}_{dataset_hash[:10]}_{embed_hash}"


def _reset_evaluation_collection(rag_assistant) -> None:
    """Recreate only a dedicated evaluation collection, never a user collection."""
    vector_db = rag_assistant.knowledge_base.vector_db
    collection = str(getattr(vector_db, "collection", ""))
    if not collection.startswith("autosar_eval_"):
        raise RuntimeError(
            "Refusing to reset a non-evaluation Qdrant collection. "
            f"Received collection={collection!r}."
        )
    client = getattr(vector_db, "client", None)
    if client is None or not hasattr(client, "delete_collection"):
        raise RuntimeError("Qdrant client cannot reset the isolated evaluation collection.")

    # The evaluation tool is intended for one local run at a time. The stable
    # collection name lets reruns replace stale vectors for the exact benchmark.
    client.delete_collection(collection_name=collection)
    vector_db.create()


def index_document_fresh(rag_assistant, pdf_path: Path) -> Dict[str, Any]:
    """Reset the evaluation-only collection and index the exact benchmark PDF."""
    from phi.document import Document
    from autosar_rag.autosar_loader import AutosarLoader
    from autosar_rag.autosar_splitter import AutosarSplitter

    if not pdf_path.exists():
        raise FileNotFoundError(f"Benchmark PDF not found: {pdf_path}")
    _reset_evaluation_collection(rag_assistant)

    with pdf_path.open("rb") as handle:
        loader = AutosarLoader(
            handle,
            document_version=sha256_file(pdf_path)[:12],
            project_id="evaluation",
        )
        raw_docs = loader.load()

    if not raw_docs:
        raise RuntimeError(f"No pages were extracted from benchmark PDF: {pdf_path.name}")
    empty_pages = [d.metadata.get("page_number") for d in raw_docs if not d.page_content.strip()]
    splitter = AutosarSplitter(chunk_size=1200, chunk_overlap=200)
    split_docs = splitter.split_documents(raw_docs)
    if not split_docs:
        raise RuntimeError("The benchmark PDF produced no non-empty chunks.")

    source_hash = sha256_file(pdf_path)
    phi_docs = []
    for doc in split_docs:
        clean_text = (getattr(doc, "page_content", "") or "").strip()
        if not clean_text:
            continue
        metadata = dict(doc.metadata or {})
        metadata["evaluation_source_sha256"] = source_hash
        metadata["evaluation_corpus"] = "autosar_large_data_com"
        phi_docs.append(
            Document(
                content=clean_text,
                name=str(metadata.get("source") or pdf_path.name),
                meta_data=metadata,
            )
        )
    if not phi_docs:
        raise RuntimeError("The benchmark PDF produced no valid non-empty chunks after filtering.")
    rag_assistant.knowledge_base.load_documents(phi_docs, upsert=True)

    vector_db = rag_assistant.knowledge_base.vector_db
    client = getattr(vector_db, "client", None)
    if client is not None and hasattr(client, "count"):
        count_result = client.count(collection_name=vector_db.collection, exact=True)
        indexed_count = int(getattr(count_result, "count", -1))
        if indexed_count != len(phi_docs):
            raise RuntimeError(
                "Evaluation index count does not match submitted chunks: "
                f"expected {len(phi_docs)}, found {indexed_count}."
            )
    else:
        indexed_count = None

    return {
        "pdf_name": pdf_path.name,
        "pdf_sha256": source_hash,
        "pages_extracted": len(raw_docs),
        "empty_pages": empty_pages,
        "chunks_indexed": len(phi_docs),
        "qdrant_count": indexed_count,
        "collection": vector_db.collection,
    }


def _response_to_text(response: Any) -> str:
    if isinstance(response, str):
        return response.strip()
    if isinstance(getattr(response, "content", None), str):
        return response.content.strip()
    parts: list[str] = []
    try:
        for delta in response:
            if isinstance(delta, str):
                parts.append(delta)
            elif isinstance(getattr(delta, "content", None), str):
                parts.append(delta.content)
            elif getattr(delta, "content", None) is not None:
                parts.append(str(delta.content))
    except TypeError:
        return str(response).strip()
    return "".join(parts).strip()


def _capture_retrieval_trace(rag_assistant: Any, question: str, limit: int = 12) -> Dict[str, Any]:
    """Capture a diagnostic source snapshot for an evaluation question.

    Phi may perform its own retrieval inside ``Assistant.run``. This additional
    snapshot is diagnostic evidence for failure analysis; it must not be treated
    as a guaranteed byte-for-byte record of the context assembled internally.
    """
    try:
        candidates = rag_assistant.knowledge_base.search(question) or []
    except Exception as exc:
        return {
            "status": "retrieval_trace_failed",
            "error": f"{type(exc).__name__}: {exc}",
            "candidates": [],
        }

    trace: list[Dict[str, Any]] = []
    for rank, doc in enumerate(candidates[:limit], start=1):
        metadata = getattr(doc, "meta_data", None) or getattr(doc, "metadata", None) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        text = getattr(doc, "content", None) or getattr(doc, "page_content", None) or ""
        trace.append({
            "rank": rank,
            "source": metadata.get("source") or getattr(doc, "name", None),
            "document_id": metadata.get("document_id"),
            "document_version": metadata.get("document_version"),
            "page_number": metadata.get("page_number") or metadata.get("page_start"),
            "section_path": metadata.get("section_path") or metadata.get("section_headings", []),
            "chunk_id": metadata.get("chunk_id"),
            "source_sha256": metadata.get("source_sha256") or metadata.get("evaluation_source_sha256"),
            "snippet": str(text).strip()[:1200],
        })
    return {"status": "captured", "candidates": trace}


def _write_report(payload: Dict[str, Any], report_path: Path) -> None:
    results = payload.get("results", [])
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("# AUTOSAR Large Data COM Evaluation Report\n\n")
        handle.write("> **Metric limitation:** keyword coverage checks required phrases only. It is not factual accuracy, groundedness, or citation validity.\n\n")
        for key, label in [
            ("run_timestamp_utc", "Run timestamp (UTC)"),
            ("llm_model", "LLM model"),
            ("embeddings_model", "Embedding model"),
            ("dataset_name", "Dataset"),
            ("dataset_sha256", "Dataset SHA-256"),
            ("source_pdf", "Source PDF"),
            ("source_pdf_sha256", "Source PDF SHA-256"),
            ("evaluation_collection", "Evaluation collection"),
            ("total_questions", "Questions evaluated"),
            ("dataset_questions", "Questions in dataset"),
            ("is_partial_run", "Partial run"),
            ("average_keyword_coverage_pct", "Average keyword coverage"),
        ]:
            handle.write(f"- **{label}:** `{payload.get(key)}`\n")
        handle.write("\n## Results by question\n\n")
        for result in results:
            score = result.get("coverage_score")
            score_text = "not scored" if score is None else f"{score * 100:.1f}%"
            handle.write(f"### {result.get('id')}: {result.get('question', '')}\n\n")
            handle.write(f"- Category: `{result.get('category')}`; difficulty: `{result.get('difficulty')}`\n")
            handle.write(f"- Source pages: `{result.get('source_pages')}`\n")
            handle.write(f"- Keyword coverage: `{score_text}`; status: `{result.get('status')}`\n\n")
            handle.write(f"**Expected answer**\n\n{result.get('expected_answer', '')}\n\n")
            handle.write(f"**Generated answer**\n\n{result.get('generated_answer', '')}\n\n")
            handle.write(f"- Matched criteria: `{', '.join(result.get('matched_terms', [])) or 'None'}`\n")
            handle.write(f"- Missing criteria: `{', '.join(result.get('missing_terms', [])) or 'None'}`\n")
            trace = result.get("retrieval_trace", {})
            handle.write(f"- Retrieval trace status: `{trace.get('status', 'not captured')}`\n")
            if trace.get("error"):
                handle.write(f"- Retrieval trace error: `{trace['error']}`\n")
            for candidate in trace.get("candidates", []):
                source = candidate.get("source") or "unknown source"
                page = candidate.get("page_number")
                chunk_id = candidate.get("chunk_id") or "unknown chunk"
                handle.write(f"  - Rank {candidate.get('rank')}: `{source}` page `{page}` chunk `{chunk_id}`\n")
                snippet = str(candidate.get("snippet", "")).replace("\n", " ")
                if snippet:
                    handle.write(f"    - `{snippet[:400]}`\n")
            handle.write("\n---\n\n")


def answer_dataset(
    dataset_path: Path = DEFAULT_DATASET,
    llm_model: str = "qwen2.5-coder:1.5b",
    embeddings_model: str = "all-minilm:l6-v2",
    limit: Optional[int] = None,
    question_ids: Optional[set[str]] = None,
    output_json: Path = OUTPUT_JSON,
    output_report: Path = OUTPUT_REPORT,
) -> Dict[str, Any]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Benchmark source PDF not found: {PDF_PATH}")
    if limit is not None and limit < 1:
        raise ValueError("limit must be >= 1 when supplied; omit it to evaluate the full dataset")

    questions_data = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(questions_data, list) or not questions_data:
        raise ValueError("Evaluation dataset must be a non-empty JSON array.")
    dataset_questions = len(questions_data)
    if question_ids is not None:
        selected = {str(value) for value in question_ids}
        questions_data = [row for row in questions_data if str(row.get("id", "")) in selected]
        missing = selected - {str(row.get("id", "")) for row in questions_data}
        if missing:
            raise ValueError(f"Question IDs not present in dataset: {', '.join(sorted(missing))}")
    if limit is not None:
        questions_data = questions_data[:limit]
    if not questions_data:
        raise ValueError("No questions selected for evaluation.")

    dataset_hash = sha256_file(dataset_path)
    source_hash = sha256_file(PDF_PATH)
    collection = evaluation_collection_name(PDF_PATH, dataset_path, embeddings_model)
    print(f"[+] Evaluating {len(questions_data)}/{dataset_questions} questions from {dataset_path.name}")
    print(f"[+] Source SHA-256: {source_hash}")
    print(f"[+] Dataset SHA-256: {dataset_hash}")
    print(f"[+] Using isolated collection: {collection}")

    from assistant.assistant import get_rag_assistant

    rag_assistant = get_rag_assistant(
        llm_model=llm_model,
        embeddings_model=embeddings_model,
        collection_name=collection,
        project_id="evaluation",
        num_documents=12,
    )
    index_stats = index_document_fresh(rag_assistant, PDF_PATH)

    results: list[Dict[str, Any]] = []
    scored_values: list[float] = []
    for index, item in enumerate(questions_data, start=1):
        question_id = item.get("id", f"Q-{index}")
        question = str(item.get("question", ""))
        print(f"\n[{index}/{len(questions_data)}] [{question_id}] {question}")
        retrieval_trace = _capture_retrieval_trace(rag_assistant, question)
        try:
            answer = _response_to_text(rag_assistant.run(question))
        except Exception as exc:
            answer = ""
            error = f"{type(exc).__name__}: {exc}"
        else:
            error = None

        score_result = check_must_include(answer, item.get("must_include", ""))
        score = score_result.get("score")
        if score is not None:
            scored_values.append(float(score))
            status = "PASS" if score >= 0.8 else ("PARTIAL" if score > 0 else "FAIL")
        else:
            status = "NOT SCORED"
        results.append({
            "id": question_id,
            "category": item.get("category", "general"),
            "difficulty": item.get("difficulty", "medium"),
            "question": question,
            "source_pages": item.get("source_pages", ""),
            "expected_answer": item.get("expected_answer", ""),
            "must_include": item.get("must_include", ""),
            "generated_answer": answer,
            "generation_error": error,
            "coverage_score": score,
            "status": status,
            "matched_terms": score_result.get("matched", []),
            "missing_terms": score_result.get("missing", []),
            "criteria_scored": score_result.get("scored", False),
            "retrieval_trace": retrieval_trace,
        })
        print(f"Status: {status}; keyword coverage: {('not scored' if score is None else f'{score * 100:.1f}%')}")
        if error:
            print(f"Generation error: {error}")

    average = (sum(scored_values) / len(scored_values) * 100) if scored_values else None
    payload: Dict[str, Any] = {
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "llm_model": llm_model,
        "embeddings_model": embeddings_model,
        "dataset_name": dataset_path.name,
        "dataset_sha256": dataset_hash,
        "source_pdf": PDF_PATH.name,
        "source_pdf_sha256": source_hash,
        "evaluation_collection": index_stats["collection"],
        "index_stats": index_stats,
        "total_questions": len(questions_data),
        "dataset_questions": dataset_questions,
        "question_ids": [result["id"] for result in results],
        "is_partial_run": len(questions_data) != dataset_questions,
        "scored_question_count": len(scored_values),
        "average_keyword_coverage_pct": None if average is None else round(average, 2),
        # Backwards compatibility for consumers of the previous JSON artifact.
        "average_coverage_pct": None if average is None else round(average, 2),
        "results": results,
    }
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_report(payload, output_report)
    print(f"\nAverage keyword coverage: {('not scored' if average is None else f'{average:.2f}%')}")
    print(f"Results: {output_json}")
    print(f"Report: {output_report}")
    return {"average_keyword_coverage_pct": payload["average_keyword_coverage_pct"], "total_questions": len(results), "is_partial_run": payload["is_partial_run"], "report": str(output_report), "results_json": str(output_json)}


def answer_single_question(
    question_id: str,
    llm_model: str = "qwen2.5-coder:1.5b",
    embeddings_model: str = "all-minilm:l6-v2",
) -> Dict[str, Any]:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(question_id))
    return answer_dataset(
        question_ids={str(question_id)},
        llm_model=llm_model,
        embeddings_model=embeddings_model,
        output_json=WORKSPACE_DIR / f"evaluation_{safe_id}_answers.json",
        output_report=WORKSPACE_DIR / f"evaluation_{safe_id}_report.md",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate AUTOSAR answers against a fixed benchmark.")
    parser.add_argument("--limit", type=int, help="Evaluate the first N questions; default runs the full dataset")
    parser.add_argument("--question-id", type=str, help="Evaluate one question ID")
    parser.add_argument("--llm-model", default="qwen2.5-coder:1.5b")
    parser.add_argument("--embeddings-model", default="all-minilm:l6-v2")
    args = parser.parse_args()
    if args.question_id:
        answer_single_question(args.question_id, llm_model=args.llm_model, embeddings_model=args.embeddings_model)
    else:
        answer_dataset(limit=args.limit, llm_model=args.llm_model, embeddings_model=args.embeddings_model)
