#!/usr/bin/env python3
"""
Chunk Context Formatter - Instruction 5: Give every chunk enough context to stand alone.

Formats standalone chunks with:
- Short heading context prefix embedded alongside the body for dense vector embedding
- Pure source text maintained separately
- Standardized metadata contract with strict null policy for unknown page numbers
- JSONL export and inspection utilities
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from structured_chunker import StructuredChunk

logger = logging.getLogger(__name__)


@dataclass
class ExportableChunk:
    """Standardized metadata schema for standalone retrieval & fine-tuning."""
    document_id: str
    document_version: str
    chunk_id: str
    section_path: str
    page_start: Optional[int]
    page_end: Optional[int]
    chunk_index: int
    parent_section_id: Optional[str]
    token_count: int
    quality_flags: List[str]
    source_text: str
    embedding_text: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_version": self.document_version,
            "chunk_id": self.chunk_id,
            "section_path": self.section_path,
            "page_start": self.page_start,  # null if unknown, never inferred
            "page_end": self.page_end,      # null if unknown
            "chunk_index": self.chunk_index,
            "parent_section_id": self.parent_section_id,
            "token_count": self.token_count,
            "quality_flags": self.quality_flags,
            "source_text": self.source_text,
            "embedding_text": self.embedding_text,
            "created_at": self.created_at
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class ChunkContextFormatter:
    """Formats and exports chunks with contextual prefixes and structured metadata."""

    @staticmethod
    def format_chunk(chunk: StructuredChunk) -> ExportableChunk:
        """Convert a StructuredChunk into an ExportableChunk."""
        return ExportableChunk(
            document_id=chunk.document_id,
            document_version=chunk.document_version,
            chunk_id=chunk.chunk_id,
            section_path=chunk.section_path,
            page_start=chunk.page_start if isinstance(chunk.page_start, int) else None,
            page_end=chunk.page_end if isinstance(chunk.page_end, int) else None,
            chunk_index=chunk.chunk_index,
            parent_section_id=chunk.parent_section_id,
            token_count=chunk.token_count,
            quality_flags=list(chunk.quality_flags),
            source_text=chunk.source_text,
            embedding_text=chunk.embedding_text,
            created_at=chunk.created_at
        )

    @classmethod
    def export_chunks_jsonl(cls, chunks: List[StructuredChunk], output_file: str) -> int:
        """Export a list of chunks to a JSONL file."""
        count = 0
        with open(output_file, 'w', encoding='utf-8') as f:
            for c in chunks:
                exp = cls.format_chunk(c)
                f.write(exp.to_json() + '\n')
                count += 1
        return count

    @classmethod
    def export_chatgpt_jsonl(
        cls,
        chunks: List[StructuredChunk],
        output_file: str,
        system_prompt: str = "You are a helpful expert assistant specializing in social media strategy and execution."
    ) -> int:
        """Export chunks into OpenAI ChatGPT fine-tuning JSONL format."""
        count = 0
        with open(output_file, 'w', encoding='utf-8') as f:
            for c in chunks:
                # Exclude pure promotional or TOC chunks from fine-tuning dataset
                if any(flag in ["is_toc", "is_promotional"] for flag in c.quality_flags):
                    continue

                # Generate high-quality instruction prompt from section path
                prompt = f"Explain the key principles and actionable steps for: {c.section_path}"
                record = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": c.source_text}
                    ],
                    "metadata": {
                        "chunk_id": c.chunk_id,
                        "document_id": c.document_id,
                        "section_path": c.section_path,
                        "token_count": c.token_count,
                        "page_start": c.page_start,
                        "page_end": c.page_end
                    }
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                count += 1
        return count
