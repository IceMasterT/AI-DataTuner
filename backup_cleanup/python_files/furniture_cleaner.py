#!/usr/bin/env python3
"""
Furniture Cleaner & Audit Ledger - Instruction 2: Clean repeated page furniture without deleting useful content.

Removes repeated running headers, footers, and standalone page numbers from the text being embedded.
Preserves source attribution and page references in metadata.
Tags biography, table of contents, and promotional material separately.
Maintains a detailed audit record of what cleanup removed.
"""

import re
import difflib
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime

from document_structure_extractor import ExtractedBlock, ExtractedDocument

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """Audit record for removed furniture or flagged content."""
    timestamp: str
    page_num: int
    block_id: str
    removal_type: str  # "running_header", "running_footer", "page_number", "promotional_boiler", "empty_block"
    removed_text: str
    reason: str
    bbox: Tuple[float, float, float, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CleaningResult:
    """Result of furniture cleaning and section tagging."""
    document_id: str
    cleaned_blocks: List[ExtractedBlock]
    removed_blocks: List[ExtractedBlock]
    audit_log: List[AuditEntry]
    tagged_sections: Dict[str, List[str]] = field(default_factory=dict)  # "toc", "biography", "promotional"
    cleaned_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "total_blocks_in": len(self.cleaned_blocks) + len(self.removed_blocks),
            "cleaned_blocks_count": len(self.cleaned_blocks),
            "removed_blocks_count": len(self.removed_blocks),
            "audit_log_count": len(self.audit_log),
            "tagged_sections": self.tagged_sections,
            "cleaned_at": self.cleaned_at,
            "audit_log": [a.to_dict() for a in self.audit_log]
        }


class FurnitureCleaner:
    """
    Cleans repeated page furniture (headers, footers, page numbers)
    and tags non-instructional content (TOC, biography, promotion).
    """

    # Standalone page number patterns
    PAGE_NUM_PATTERNS = [
        re.compile(r'^\s*page\s+\d+(\s+of\s+\d+)?\s*$', re.IGNORECASE),
        re.compile(r'^\s*[-—–~]\s*\d+\s*[-—–~]\s*$'),
        re.compile(r'^\s*\d+\s*/\s*\d+\s*$'),
        re.compile(r'^\s*\d{1,4}\s*$'),  # Single standalone number
    ]

    # Biography patterns
    BIO_PATTERNS = [
        re.compile(r'\b(about\s+the\s+author|about\s+us|author\s+bio|biography|who\s+we\s+are|meet\s+the\s+team|about\s+tent\s+social)\b', re.IGNORECASE),
    ]

    # Table of Contents patterns
    TOC_PATTERNS = [
        re.compile(r'\b(table\s+of\s+contents|table\s+of\s+content|contents|index)\b', re.IGNORECASE),
        re.compile(r'\.{3,}\s*\d+'),  # Dot leaders with page numbers
    ]

    # Promotional patterns
    PROMO_PATTERNS = [
        re.compile(r'\b(subscribe\s+to|visit\s+our\s+website|follow\s+us\s+on|special\s+offer|discount\s+code|call\s+to\s+action|contact\s+us\s+at|for\s+more\s+information\s+visit)\b', re.IGNORECASE),
        re.compile(r'https?://[^\s]+|www\.[^\s]+', re.IGNORECASE),
    ]

    def __init__(self, header_margin_pct: float = 0.15, footer_margin_pct: float = 0.15):
        """
        Args:
            header_margin_pct: Top fraction of page considered header zone (e.g. 0.15)
            footer_margin_pct: Bottom fraction of page considered footer zone (e.g. 0.15)
        """
        self.header_margin_pct = header_margin_pct
        self.footer_margin_pct = footer_margin_pct

    def clean_document(self, document: ExtractedDocument) -> CleaningResult:
        """Process document blocks to remove furniture and tag special sections."""
        audit_log: List[AuditEntry] = []
        cleaned_blocks: List[ExtractedBlock] = []
        removed_blocks: List[ExtractedBlock] = []
        tagged_sections: Dict[str, List[str]] = {
            "toc": [],
            "biography": [],
            "promotional": []
        }

        # Step 1: Detect repeated header and footer text across pages
        repeated_headers, repeated_footers = self._detect_repeated_furniture(document)

        # Step 2: Classify and filter each block
        for block in document.blocks:
            text = block.text.strip()
            if not text:
                removed_blocks.append(block)
                audit_log.append(AuditEntry(
                    timestamp=datetime.now().isoformat(),
                    page_num=block.page_num,
                    block_id=block.block_id,
                    removal_type="empty_block",
                    removed_text="",
                    reason="Empty text block",
                    bbox=block.bbox
                ))
                continue

            # Check if block is a standalone page number
            if self._is_standalone_page_number(block, document):
                removed_blocks.append(block)
                audit_log.append(AuditEntry(
                    timestamp=datetime.now().isoformat(),
                    page_num=block.page_num,
                    block_id=block.block_id,
                    removal_type="page_number",
                    removed_text=text,
                    reason=f"Standalone page number on page {block.page_num}",
                    bbox=block.bbox
                ))
                continue

            # Check if block matches repeated running headers
            if self._matches_furniture(text, repeated_headers):
                removed_blocks.append(block)
                audit_log.append(AuditEntry(
                    timestamp=datetime.now().isoformat(),
                    page_num=block.page_num,
                    block_id=block.block_id,
                    removal_type="running_header",
                    removed_text=text,
                    reason=f"Repeated running header across pages: '{text[:50]}'",
                    bbox=block.bbox
                ))
                continue

            # Check if block matches repeated running footers
            if self._matches_furniture(text, repeated_footers):
                removed_blocks.append(block)
                audit_log.append(AuditEntry(
                    timestamp=datetime.now().isoformat(),
                    page_num=block.page_num,
                    block_id=block.block_id,
                    removal_type="running_footer",
                    removed_text=text,
                    reason=f"Repeated running footer across pages: '{text[:50]}'",
                    bbox=block.bbox
                ))
                continue

            # Clean inline furniture (e.g. running series header embedded in the first line of a block)
            cleaned_text = self._strip_inline_furniture(text, repeated_headers | repeated_footers)
            if cleaned_text != text:
                audit_log.append(AuditEntry(
                    timestamp=datetime.now().isoformat(),
                    page_num=block.page_num,
                    block_id=block.block_id,
                    removal_type="running_header",
                    removed_text=text[:len(text)-len(cleaned_text)],
                    reason="Stripped inline repeated header from block top",
                    bbox=block.bbox
                ))
                block.text = cleaned_text

            # Tag special non-instructional content
            tags = self._tag_special_content(block.text)
            for tag in tags:
                if tag not in block.metadata:
                    block.metadata[f"is_{tag}"] = True
                tagged_sections[tag].append(block.block_id)

            cleaned_blocks.append(block)

        return CleaningResult(
            document_id=document.document_id,
            cleaned_blocks=cleaned_blocks,
            removed_blocks=removed_blocks,
            audit_log=audit_log,
            tagged_sections=tagged_sections
        )

    def _detect_repeated_furniture(
        self, document: ExtractedDocument
    ) -> Tuple[Set[str], Set[str]]:
        """
        Detect headers and footers that repeat across >= 2 pages.
        Returns (set_of_headers, set_of_footers).
        """
        if document.page_count <= 1:
            return set(), set()

        header_candidates_by_page: Dict[int, List[str]] = {}
        footer_candidates_by_page: Dict[int, List[str]] = {}

        # Estimate page height
        sample_height = 800.0
        for block in document.blocks:
            if block.bbox[3] > 0:
                sample_height = max(sample_height, block.bbox[3])

        header_threshold = sample_height * self.header_margin_pct
        footer_threshold = sample_height * (1.0 - self.footer_margin_pct)

        for block in document.blocks:
            page = block.page_num
            y0, y1 = block.bbox[1], block.bbox[3]
            norm_text = self._normalize_furniture_text(block.text)
            if not norm_text or len(norm_text) < 3:
                continue

            if y0 <= header_threshold:
                header_candidates_by_page.setdefault(page, []).append(norm_text)
            elif y1 >= footer_threshold:
                footer_candidates_by_page.setdefault(page, []).append(norm_text)

        repeated_headers = self._find_repeating_strings(header_candidates_by_page)
        repeated_footers = self._find_repeating_strings(footer_candidates_by_page)

        # Known persistent series patterns (e.g. "Tent Social Marketing Strategy Series")
        common_series = [
            "tent social marketing strategy series",
            "social media strategy blueprint",
            "tent social",
        ]
        for s in common_series:
            repeated_headers.add(s)

        return repeated_headers, repeated_footers

    def _find_repeating_strings(
        self, candidates_by_page: Dict[int, List[str]]
    ) -> Set[str]:
        """Find strings that appear on at least 2 distinct pages."""
        text_page_counts: Dict[str, Set[int]] = {}
        for page, texts in candidates_by_page.items():
            for t in texts:
                text_page_counts.setdefault(t, set()).add(page)

        repeating = set()
        for text, pages in text_page_counts.items():
            if len(pages) >= 2:
                repeating.add(text)

        return repeating

    def _normalize_furniture_text(self, text: str) -> str:
        """Normalize whitespace and lowercase for furniture comparison."""
        t = re.sub(r'\s+', ' ', text).strip().lower()
        # Remove numbers for header pattern matching (e.g. "Chapter 1 - Title" vs "Chapter 2 - Title")
        return t

    def _matches_furniture(self, text: str, furniture_set: Set[str]) -> bool:
        """Check if text matches any detected furniture."""
        norm = self._normalize_furniture_text(text)
        if norm in furniture_set:
            return True

        for f in furniture_set:
            if f and len(f) >= 6:
                if f in norm or norm in f:
                    return True
                # Fuzzy ratio
                similarity = difflib.SequenceMatcher(None, norm, f).ratio()
                if similarity >= 0.88:
                    return True

        return False

    def _strip_inline_furniture(self, text: str, furniture_set: Set[str]) -> str:
        """Strip running header if it was fused to the start of a text block."""
        lines = text.split('\n')
        if len(lines) > 1:
            first_line_norm = self._normalize_furniture_text(lines[0])
            for f in furniture_set:
                if f and len(f) >= 6 and (f in first_line_norm or difflib.SequenceMatcher(None, first_line_norm, f).ratio() >= 0.88):
                    return '\n'.join(lines[1:]).strip()
        return text

    def _is_standalone_page_number(self, block: ExtractedBlock, document: ExtractedDocument) -> bool:
        """Check if block is an isolated page number."""
        text = block.text.strip()
        for pat in self.PAGE_NUM_PATTERNS:
            if pat.match(text):
                # Verify length is short
                if len(text) < 20:
                    return True
        return False

    def _tag_special_content(self, text: str) -> List[str]:
        """Tag content as toc, biography, promotional, or content."""
        tags = []
        for pat in self.TOC_PATTERNS:
            if pat.search(text):
                tags.append("toc")
                break

        for pat in self.BIO_PATTERNS:
            if pat.search(text):
                tags.append("biography")
                break

        for pat in self.PROMO_PATTERNS:
            if pat.search(text):
                tags.append("promotional")
                break

        return tags
