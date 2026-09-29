#!/usr/bin/env python3
"""
Chunk Validator & Manifest Ledger - Instruction 6: Add validation before embedding.

Performs pre-embedding validation:
- Flags chunks with garbled text, empty bodies, detached headings, or multiple unrelated sections.
- Tracks source blocks (included, excluded, held for review) so content cannot silently disappear.
- Ensures reimporting a document replaces previous chunks without duplicates.
- Validates completeness across the numbered steps/chapters/parts/modules the document itself evidences
  (source headings, or a count declared in the title such as "Ten Step ...").
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from document_structure_extractor import ExtractedBlock, GarbledTextDetector, ExtractedDocument
from structured_chunker import StructuredChunk

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """An issue detected during chunk validation."""
    chunk_id: str
    issue_type: str  # "garbled_text", "empty_body", "detached_heading", "cross_section_leakage", "incomplete_coverage", "numbering_gap"
    severity: str  # "error", "warning"
    message: str
    sample_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceBlockManifest:
    """Ledger tracking the fate of every source block in extraction."""
    document_id: str
    total_blocks: int
    included_blocks: List[str] = field(default_factory=list)
    excluded_blocks: List[Dict[str, Any]] = field(default_factory=list)
    held_for_review_blocks: List[Dict[str, Any]] = field(default_factory=list)
    inclusion_rate: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "total_blocks": self.total_blocks,
            "included_count": len(self.included_blocks),
            "excluded_count": len(self.excluded_blocks),
            "held_for_review_count": len(self.held_for_review_blocks),
            "inclusion_rate": self.inclusion_rate,
            "created_at": self.created_at,
            "included_blocks": self.included_blocks,
            "excluded_blocks": self.excluded_blocks,
            "held_for_review_blocks": self.held_for_review_blocks
        }


@dataclass
class ValidationReport:
    """Comprehensive validation report for document chunks."""
    document_id: str
    is_valid: bool
    total_chunks: int
    valid_chunks_count: int
    flagged_chunks_count: int
    issues: List[ValidationIssue]
    steps_detected: List[str]
    missing_expected_steps: List[str]
    manifest: SourceBlockManifest
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "is_valid": self.is_valid,
            "total_chunks": self.total_chunks,
            "valid_chunks_count": self.valid_chunks_count,
            "flagged_chunks_count": self.flagged_chunks_count,
            "steps_detected": self.steps_detected,
            "missing_expected_steps": self.missing_expected_steps,
            "manifest_summary": {
                "total_blocks": self.manifest.total_blocks,
                "included": len(self.manifest.included_blocks),
                "excluded": len(self.manifest.excluded_blocks),
                "held": len(self.manifest.held_for_review_blocks),
                "inclusion_rate": f"{self.manifest.inclusion_rate * 100:.1f}%"
            },
            "issues_count": len(self.issues),
            "issues": [i.to_dict() for i in self.issues],
            "validated_at": self.validated_at
        }


class ChunkValidator:
    """Validates chunks, audits block manifests, and checks document completeness."""

    # Numbered structural units the document may be organised into
    UNIT_KINDS = ("Step", "Chapter", "Part", "Module")

    _NUMBER_WORDS = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
        "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20,
    }
    _NUMBER_PATTERN = r"\d{1,3}|" + "|".join(_NUMBER_WORDS)
    _KIND_PATTERN = "|".join(UNIT_KINDS)
    # "Step 3", "Chapter Four" ...
    _UNIT_RE = re.compile(rf"\b({_KIND_PATTERN})\s+({_NUMBER_PATTERN})\b", re.IGNORECASE)
    # A title declaring its own size: "Ten Step Blueprint", "The 7 Chapters of ..."
    _DECLARED_RE = re.compile(rf"\b({_NUMBER_PATTERN})[\s-]+({_KIND_PATTERN})s?\b", re.IGNORECASE)

    @classmethod
    def _to_int(cls, token: str) -> int:
        token = token.lower()
        return int(token) if token.isdigit() else cls._NUMBER_WORDS[token]

    @classmethod
    def _units_in(cls, text: str) -> Dict[str, Set[int]]:
        """Numbered units mentioned in `text`, keyed by kind (Step, Chapter, ...)."""
        found: Dict[str, Set[int]] = {}
        for kind, num in cls._UNIT_RE.findall(text):
            found.setdefault(kind.title(), set()).add(cls._to_int(num))
        return found

    @classmethod
    def _declared_units(cls, title_text: str) -> Dict[str, int]:
        """Unit counts the document title promises (e.g. 'Ten Step ...' -> {'Step': 10})."""
        return {kind.title(): cls._to_int(num) for num, kind in cls._DECLARED_RE.findall(title_text)}

    def _check_unit_coverage(
        self,
        chunks: List[StructuredChunk],
        extracted_doc: ExtractedDocument,
    ) -> Tuple[List[str], List[str], List[ValidationIssue]]:
        """
        Check that every numbered unit the document itself evidences made it into chunks.

        A unit is expected when the source has a heading for it, or the title declares
        a count that covers it. Documents with no numbered structure are not checked.
        """
        doc_id = extracted_doc.document_id
        title_text = doc_id.replace("_", " ").replace("-", " ")
        if chunks:
            title_text += " " + chunks[0].section_path.split(" > ")[0]

        declared = self._declared_units(title_text)

        source_units: Dict[str, Set[int]] = {}
        for block in extracted_doc.blocks:
            first_line = block.text.strip().split("\n")[0]
            if block.is_heading or self._UNIT_RE.match(first_line):
                for kind, nums in self._units_in(first_line).items():
                    source_units.setdefault(kind, set()).update(nums)

        chunk_units = self._units_in(" ".join(c.embedding_text for c in chunks))

        detected: List[str] = []
        missing: List[str] = []
        issues: List[ValidationIssue] = []

        for kind in sorted(set(declared) | set(source_units)):
            expected = set(source_units.get(kind, set()))
            if kind in declared:
                expected |= set(range(1, declared[kind] + 1))
            present = chunk_units.get(kind, set())

            detected.extend(f"{kind} {n}" for n in sorted(expected & present))
            missing_nums = sorted(expected - present)
            missing.extend(f"{kind} {n}" for n in missing_nums)

            if missing_nums:
                basis = (f"title declares {declared[kind]} {kind.lower()}s" if kind in declared
                         else f"source has {kind.lower()} headings up to {max(source_units[kind])}")
                issues.append(ValidationIssue(
                    chunk_id=f"{doc_id}_coverage",
                    issue_type="incomplete_coverage",
                    severity="error",
                    message=(f"Document incomplete ({basis}): missing "
                             f"{[f'{kind} {n}' for n in missing_nums]}"),
                    sample_text=f"Found {len(expected & present)} of {len(expected)} expected {kind.lower()}s in chunks"
                ))

            # Gaps inside the source's own numbering suggest the extractor dropped a heading
            observed = source_units.get(kind, set())
            gaps = sorted(set(range(1, max(observed) + 1)) - observed) if observed else []
            if gaps:
                issues.append(ValidationIssue(
                    chunk_id=f"{doc_id}_coverage",
                    issue_type="numbering_gap",
                    severity="warning",
                    message=f"Source {kind.lower()} numbering skips {gaps}; a heading may not have been extracted",
                    sample_text=""
                ))

        return detected, missing, issues

    def validate_chunks(
        self,
        chunks: List[StructuredChunk],
        extracted_doc: ExtractedDocument,
        excluded_blocks: Optional[List[ExtractedBlock]] = None
    ) -> ValidationReport:
        """Run all validation checks on chunk list."""
        issues: List[ValidationIssue] = []
        valid_chunks_count = 0
        flagged_chunks_count = 0

        included_block_ids: Set[str] = set()
        for c in chunks:
            included_block_ids.update(c.source_block_ids)

        # 1. Validate each chunk
        for chunk in chunks:
            chunk_has_issue = False

            # Check 1: Empty or near-empty body
            if not chunk.source_text or len(chunk.source_text.strip()) < 15:
                issues.append(ValidationIssue(
                    chunk_id=chunk.chunk_id,
                    issue_type="empty_body",
                    severity="error",
                    message="Chunk has empty or trivial body content",
                    sample_text=chunk.source_text
                ))
                chunk.quality_flags.append("empty_body_flagged")
                chunk_has_issue = True

            # Check 2: Garbled or corrupted text
            is_garbled, reason = GarbledTextDetector.analyze_text(chunk.source_text)
            if is_garbled:
                issues.append(ValidationIssue(
                    chunk_id=chunk.chunk_id,
                    issue_type="garbled_text",
                    severity="error",
                    message=f"Garbled text detected: {reason}",
                    sample_text=chunk.source_text[:100]
                ))
                chunk.quality_flags.append("garbled_flagged")
                chunk_has_issue = True

            # Check 3: Detached heading (heading without body, or body without section path)
            if not chunk.section_path or chunk.section_path.strip() == "":
                issues.append(ValidationIssue(
                    chunk_id=chunk.chunk_id,
                    issue_type="detached_heading",
                    severity="warning",
                    message="Chunk has missing or empty section_path",
                    sample_text=chunk.source_text[:100]
                ))
                chunk_has_issue = True

            # Check 4: Cross-section leakage (detect if multiple distinct Step headings appear inside one chunk body)
            step_matches = re.findall(r'\b(Step\s+(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|[0-9]+))\b', chunk.source_text, re.IGNORECASE)
            distinct_steps = set(s.title() for s in step_matches)
            if len(distinct_steps) > 1 and not any("toc" in f for f in chunk.quality_flags):
                issues.append(ValidationIssue(
                    chunk_id=chunk.chunk_id,
                    issue_type="cross_section_leakage",
                    severity="warning",
                    message=f"Multiple unrelated steps detected in single chunk: {list(distinct_steps)}",
                    sample_text=chunk.source_text[:100]
                ))
                chunk.quality_flags.append("cross_section_leakage_flagged")
                chunk_has_issue = True

            if chunk_has_issue:
                flagged_chunks_count += 1
            else:
                valid_chunks_count += 1

        # 2. Build Source Block Manifest Ledger
        excluded_list = []
        if excluded_blocks:
            for eb in excluded_blocks:
                excluded_list.append({
                    "block_id": eb.block_id,
                    "page_num": eb.page_num,
                    "text_preview": eb.text[:60],
                    "reason": eb.metadata.get("exclusion_reason", "furniture_removed")
                })

        held_list = []
        for b in extracted_doc.blocks:
            if b.block_id not in included_block_ids and not any(eb.block_id == b.block_id for eb in (excluded_blocks or [])):
                held_list.append({
                    "block_id": b.block_id,
                    "page_num": b.page_num,
                    "text_preview": b.text[:60],
                    "reason": "unassigned_block"
                })

        total_b = len(extracted_doc.blocks) + len(excluded_blocks or [])
        inc_rate = len(included_block_ids) / total_b if total_b > 0 else 1.0

        manifest = SourceBlockManifest(
            document_id=extracted_doc.document_id,
            total_blocks=total_b,
            included_blocks=list(included_block_ids),
            excluded_blocks=excluded_list,
            held_for_review_blocks=held_list,
            inclusion_rate=inc_rate
        )

        # 3. Check numbered-unit coverage (Step/Chapter/Part/Module)
        steps_detected, missing_steps, coverage_issues = self._check_unit_coverage(chunks, extracted_doc)
        issues.extend(coverage_issues)

        is_valid = len([i for i in issues if i.severity == "error"]) == 0

        return ValidationReport(
            document_id=extracted_doc.document_id,
            is_valid=is_valid,
            total_chunks=len(chunks),
            valid_chunks_count=valid_chunks_count,
            flagged_chunks_count=flagged_chunks_count,
            issues=issues,
            steps_detected=steps_detected,
            missing_expected_steps=missing_steps,
            manifest=manifest
        )


class DocumentStoreDeduplicator:
    """Manages document chunk replacement and deduplication."""

    def __init__(self, storage_dict: Optional[Dict[str, List[StructuredChunk]]] = None):
        self.store = storage_dict if storage_dict is not None else {}

    def replace_document_chunks(
        self, document_id: str, new_chunks: List[StructuredChunk]
    ) -> Tuple[int, int]:
        """
        Replace all existing chunks for a document without duplicates.
        Returns (replaced_count, inserted_count).
        """
        previous_count = len(self.store.get(document_id, []))
        self.store[document_id] = list(new_chunks)
        logger.info(f"Replaced {previous_count} previous chunks with {len(new_chunks)} new chunks for '{document_id}'")
        return previous_count, len(new_chunks)

    def get_document_chunks(self, document_id: str) -> List[StructuredChunk]:
        return self.store.get(document_id, [])
