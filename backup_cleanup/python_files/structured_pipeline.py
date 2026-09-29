#!/usr/bin/env python3
"""
Single entry point for the structure-aware pipeline:
extract -> clean furniture -> section hierarchy -> chunk -> validate -> export.

Shared by the workflow orchestrator (`start` / `process` CLI commands) and the
retrieval benchmark so they run exactly the same stages.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from chunk_context_formatter import ChunkContextFormatter
from chunk_validator import ChunkValidator, ValidationReport
from document_structure_extractor import DocumentStructureExtractor, ExtractedDocument
from furniture_cleaner import CleaningResult, FurnitureCleaner
from section_hierarchy_builder import DocumentHierarchy, SectionHierarchyBuilder
from structured_chunker import StructuredChunk, StructuredChunker

logger = logging.getLogger(__name__)

STRUCTURED_EXTENSIONS = {".pdf", ".txt", ".md"}


@dataclass
class StructuredPipelineResult:
    """Everything produced by one run of the structure-aware pipeline."""
    document: ExtractedDocument
    cleaning: CleaningResult
    hierarchy: DocumentHierarchy
    chunks: List[StructuredChunk]
    validation: ValidationReport
    output_files: List[str] = field(default_factory=list)


def is_supported(file_path: Path) -> bool:
    return Path(file_path).suffix.lower() in STRUCTURED_EXTENSIONS


def run_structured_pipeline(
    file_path: Path,
    output_dir: Optional[Path] = None,
    target_tokens: int = 500,
    max_tokens: int = 800,
) -> StructuredPipelineResult:
    """Run every stage on one document; write artifacts when `output_dir` is given.

    Writes `<stem>_chunks.jsonl`, `<stem>_validation_report.json` and
    `<stem>_source_manifest.json` into `output_dir`.
    """
    file_path = Path(file_path)

    document = DocumentStructureExtractor().extract_document(file_path)
    cleaning = FurnitureCleaner().clean_document(document)
    hierarchy = SectionHierarchyBuilder().build_hierarchy(cleaning.cleaned_blocks, document.document_id)
    chunks = StructuredChunker(target_tokens=target_tokens, max_tokens=max_tokens).chunk_hierarchy(hierarchy)
    validation = ChunkValidator().validate_chunks(chunks, document, cleaning.removed_blocks)

    result = StructuredPipelineResult(document, cleaning, hierarchy, chunks, validation)

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = file_path.stem

        jsonl_path = output_dir / f"{stem}_chunks.jsonl"
        ChunkContextFormatter.export_chunks_jsonl(chunks, str(jsonl_path))

        report_path = output_dir / f"{stem}_validation_report.json"
        report_path.write_text(json.dumps(validation.to_dict(), indent=2), encoding="utf-8")

        manifest_path = output_dir / f"{stem}_source_manifest.json"
        manifest_path.write_text(json.dumps(validation.manifest.to_dict(), indent=2), encoding="utf-8")

        result.output_files = [str(jsonl_path), str(report_path), str(manifest_path)]
        logger.info(
            "Structured pipeline: %s -> %d chunks (valid: %s) in %s",
            file_path.name, len(chunks), validation.is_valid, output_dir,
        )

    return result
