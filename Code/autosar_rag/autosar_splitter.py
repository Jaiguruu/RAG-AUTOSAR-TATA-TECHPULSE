"""Architecture-aware chunking with reproducible identifiers and provenance."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


from autosar_rag.sectioning import section_segments

def remove_empty_documents(documents: Iterable[Document]) -> List[Document]:
    """Filter out empty or whitespace-only documents before embedding and indexing.

    Qdrant rejects points where dense vectors are empty (HTTP 422). Filtering
    empty text documents beforehand prevents this condition.
    """
    valid_documents: List[Document] = []
    skipped = 0
    for doc in documents:
        text = getattr(doc, "page_content", "")
        if not isinstance(text, str) or not text.strip():
            skipped += 1
            continue
        valid_documents.append(doc)
    return valid_documents


class AutosarSplitter:
    """Split page records while keeping chunks large enough for technical APIs.

    This is a strong character-based baseline, not a full AUTOSAR grammar. The
    loader's page/section metadata is preserved on every chunk. Table-aware row
    splitting can be added when the loader starts emitting structured tables.
    """

    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 200):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            separators=[
                "\n\n",
                "\n",
                ";\n",
                ". ",
                "; ",
                ", ",
                " ",
                "",
            ],
            add_start_index=True,
        )

    def split_documents(self, documents: Iterable[Document]) -> List[Document]:
        chunks: List[Document] = []
        seen_chunk_ids: set[str] = set()
        validated_documents = remove_empty_documents(documents)
        for document in validated_documents:
            text = (getattr(document, "page_content", "") or "").strip()
            if not text:
                continue
            base_metadata = dict(getattr(document, "metadata", {}) or {})
            base_path = base_metadata.get("section_path") or []
            if isinstance(base_path, str):
                base_path = [base_path] if base_path else []
            else:
                base_path = [str(item) for item in base_path if item]

            # Split at obvious section headings first, then apply recursive
            # character splitting inside each section. This avoids joining two
            # adjacent sections merely because they fit in one character window.
            for section_start, section_text, local_heading in section_segments(text):
                metadata_for_section = dict(base_metadata)
                if local_heading:
                    metadata_for_section["section_heading"] = local_heading
                    metadata_for_section["section_path"] = [local_heading]
                else:
                    metadata_for_section["section_path"] = base_path
                source_docs = self.text_splitter.create_documents(
                    [section_text], metadatas=[metadata_for_section]
                )
                for local_index, chunk in enumerate(source_docs):
                    clean_text = (getattr(chunk, "page_content", "") or "").strip()
                    if not clean_text:
                        continue
                    chunk.page_content = clean_text
                    metadata = dict(chunk.metadata or {})
                    relative_start = int(metadata.get("start_index", 0) or 0)
                    absolute_start = section_start + relative_start
                    metadata["chunk_index"] = len(chunks)
                    metadata["page_chunk_index"] = local_index
                    metadata["chunk_size_chars"] = len(clean_text)
                    metadata["chunk_start_char"] = absolute_start
                    metadata["chunk_end_char"] = absolute_start + len(clean_text)
                    metadata.setdefault("content_type", "text")
                    source_id = str(metadata.get("document_id") or metadata.get("source") or "unknown")
                    page = str(metadata.get("page_number", "unknown"))
                    digest = hashlib.sha256(
                        f"{source_id}|{page}|{absolute_start}|{clean_text}".encode("utf-8")
                    ).hexdigest()[:24]
                    metadata["chunk_id"] = digest
                    if digest in seen_chunk_ids:
                        continue
                    seen_chunk_ids.add(digest)
                    chunk.metadata = metadata
                    chunks.append(chunk)
        return remove_empty_documents(chunks)

