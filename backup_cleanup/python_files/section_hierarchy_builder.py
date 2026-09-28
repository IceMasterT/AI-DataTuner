#!/usr/bin/env python3
"""
Section Hierarchy Builder - Instruction 3: Build a section hierarchy before creating chunks.

Constructs a structured document tree:
- Document: e.g. The Ten Step Social Media Strategy Blueprint
- Section: e.g. Step One — The Destination
- Subsection: e.g. Four Tips for Goal Setting
- Content: The relevant paragraphs and numbered tips

Enforces section boundaries (e.g. Step Two heading).
Prevents TOC entries or repeated page headers from starting false sections.
Ensures generic headings like 'Tools & Resources' inherit their parent section.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from document_structure_extractor import ExtractedBlock

logger = logging.getLogger(__name__)


@dataclass
class SectionNode:
    """A node in the document section tree."""
    section_id: str
    title: str
    level: int  # 0=Document, 1=Section (Step One), 2=Subsection (Four Tips), 3=Sub-subsection
    parent_id: Optional[str] = None
    section_path: str = ""  # Full hierarchical breadcrumb path
    section_type: str = "content"  # "document", "section", "subsection", "toc", "biography", "promotional", "content"
    blocks: List[ExtractedBlock] = field(default_factory=list)
    children: List['SectionNode'] = field(default_factory=list)
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    quality_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "level": self.level,
            "parent_id": self.parent_id,
            "section_path": self.section_path,
            "section_type": self.section_type,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "quality_flags": self.quality_flags,
            "block_count": len(self.blocks),
            "children_count": len(self.children),
            "children": [c.to_dict() for c in self.children]
        }


@dataclass
class DocumentHierarchy:
    """Root representation of the hierarchical document tree."""
    document_id: str
    document_title: str
    root: SectionNode
    all_sections: List[SectionNode] = field(default_factory=list)
    section_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_title": self.document_title,
            "section_count": len(self.all_sections),
            "created_at": self.created_at,
            "tree": self.root.to_dict()
        }


class SectionHierarchyBuilder:
    """Builds hierarchical section tree from cleaned document blocks."""

    # Major section boundary patterns (Level 1)
    SECTION_PATTERNS = [
        re.compile(r'^(Step\s+(?:[0-9]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(?:\s*[:—–\-]\s*.+)?)$', re.IGNORECASE),
        re.compile(r'^(Chapter\s+[0-9]+(?:\s*[:—–\-]\s*.+)?)$', re.IGNORECASE),
        re.compile(r'^(Part\s+[0-9IVX]+(?:\s*[:—–\-]\s*.+)?)$', re.IGNORECASE),
        re.compile(r'^(Module\s+[0-9]+(?:\s*[:—–\-]\s*.+)?)$', re.IGNORECASE),
    ]

    # Subsection boundary patterns (Level 2)
    SUBSECTION_PATTERNS = [
        re.compile(r'^(Four Tips for Goal Setting|Tools\s*(?:&|and)\s*Resources|Action Items|Checklist|Overview|Key Takeaways|Strategy Blueprint)$', re.IGNORECASE),
        re.compile(r'^(Define Your Goals|Identify Your Audience|Audience Persona|Choose Your Channels|Content Strategy|Measurement & Analytics)$', re.IGNORECASE),
        re.compile(r'^##\s+(.+)$'),
    ]

    # TOC detection patterns
    TOC_LINE_PATTERN = re.compile(r'\.{3,}\s*\d+|\bpage\s+\d+\b', re.IGNORECASE)

    def __init__(self, default_document_title: Optional[str] = None):
        self.default_document_title = default_document_title

    def build_hierarchy(
        self, blocks: List[ExtractedBlock], document_id: str, doc_title: Optional[str] = None
    ) -> DocumentHierarchy:
        """Build a complete hierarchical section tree from extracted blocks."""
        # 1. Infer document title if not provided
        document_title = doc_title or self.default_document_title or self._infer_document_title(blocks, document_id)

        # 2. Create root document node
        root = SectionNode(
            section_id=f"{document_id}_root",
            title=document_title,
            level=0,
            parent_id=None,
            section_path=document_title,
            section_type="document",
            page_start=blocks[0].page_num if blocks else None,
            page_end=blocks[-1].page_num if blocks else None
        )

        all_sections: List[SectionNode] = [root]
        current_section: Optional[SectionNode] = None
        current_subsection: Optional[SectionNode] = None

        section_idx = 0
        subsection_idx = 0

        for block in blocks:
            text = block.text.strip()
            if not text:
                continue

            # Check if this block is a TOC entry or within a TOC page
            if block.metadata.get("is_toc") or self._is_toc_block(text):
                # TOC blocks should be tagged and kept under a dedicated TOC node or root
                if not any(s.section_type == "toc" for s in root.children):
                    toc_node = SectionNode(
                        section_id=f"{document_id}_toc",
                        title="Table of Contents",
                        level=1,
                        parent_id=root.section_id,
                        section_path=f"{document_title} > Table of Contents",
                        section_type="toc",
                        page_start=block.page_num,
                        page_end=block.page_num,
                        quality_flags=["is_toc"]
                    )
                    root.children.append(toc_node)
                    all_sections.append(toc_node)
                
                # Append to TOC node
                for child in root.children:
                    if child.section_type == "toc":
                        child.blocks.append(block)
                        child.page_end = block.page_num
                        break
                continue

            # Check if block is Biography / About
            if block.metadata.get("is_biography") or self._is_bio_block(text):
                if not any(s.section_type == "biography" for s in root.children):
                    bio_node = SectionNode(
                        section_id=f"{document_id}_bio",
                        title="About & Biography",
                        level=1,
                        parent_id=root.section_id,
                        section_path=f"{document_title} > About & Biography",
                        section_type="biography",
                        page_start=block.page_num,
                        page_end=block.page_num,
                        quality_flags=["is_biography"]
                    )
                    root.children.append(bio_node)
                    all_sections.append(bio_node)
                for child in root.children:
                    if child.section_type == "biography":
                        child.blocks.append(block)
                        child.page_end = block.page_num
                        break
                continue

            # Check if block is Promotional
            if block.metadata.get("is_promotional"):
                if not any(s.section_type == "promotional" for s in root.children):
                    promo_node = SectionNode(
                        section_id=f"{document_id}_promo",
                        title="Promotional & External Links",
                        level=1,
                        parent_id=root.section_id,
                        section_path=f"{document_title} > Promotional & External Links",
                        section_type="promotional",
                        page_start=block.page_num,
                        page_end=block.page_num,
                        quality_flags=["is_promotional"]
                    )
                    root.children.append(promo_node)
                    all_sections.append(promo_node)
                for child in root.children:
                    if child.section_type == "promotional":
                        child.blocks.append(block)
                        child.page_end = block.page_num
                        break
                continue

            # Check for Major Section Heading (Level 1)
            is_sec, sec_title, remaining_text = self._match_section_heading(block)
            if is_sec:
                section_idx += 1
                subsection_idx = 0
                sec_id = f"{document_id}_sec_{section_idx:02d}"
                path = f"{document_title} > {sec_title}"

                current_section = SectionNode(
                    section_id=sec_id,
                    title=sec_title,
                    level=1,
                    parent_id=root.section_id,
                    section_path=path,
                    section_type="section",
                    page_start=block.page_num,
                    page_end=block.page_num
                )
                if remaining_text:
                    body_block = ExtractedBlock(
                        block_id=f"{block.block_id}_body",
                        page_num=block.page_num,
                        bbox=block.bbox,
                        text=remaining_text,
                        block_type="paragraph"
                    )
                    current_section.blocks.append(body_block)

                root.children.append(current_section)
                all_sections.append(current_section)
                current_subsection = None
                continue

            # Check for Subsection Heading (Level 2)
            is_subsec, subsec_title, remaining_text = self._match_subsection_heading(block)
            if is_subsec:
                subsection_idx += 1
                parent = current_section or root
                subsec_id = f"{parent.section_id}_sub_{subsection_idx:02d}"
                path = f"{parent.section_path} > {subsec_title}"

                current_subsection = SectionNode(
                    section_id=subsec_id,
                    title=subsec_title,
                    level=2,
                    parent_id=parent.section_id,
                    section_path=path,
                    section_type="subsection",
                    page_start=block.page_num,
                    page_end=block.page_num
                )
                if remaining_text:
                    body_block = ExtractedBlock(
                        block_id=f"{block.block_id}_body",
                        page_num=block.page_num,
                        bbox=block.bbox,
                        text=remaining_text,
                        block_type="paragraph"
                    )
                    current_subsection.blocks.append(body_block)

                parent.children.append(current_subsection)
                all_sections.append(current_subsection)
                continue

            # Standard Content Block -> Add to current active section or subsection
            target_node = current_subsection or current_section or root
            target_node.blocks.append(block)
            if target_node.page_start is None:
                target_node.page_start = block.page_num
            target_node.page_end = block.page_num

        return DocumentHierarchy(
            document_id=document_id,
            document_title=document_title,
            root=root,
            all_sections=all_sections,
            section_count=len(all_sections)
        )

    def _infer_document_title(self, blocks: List[ExtractedBlock], fallback_id: str) -> str:
        """Infer document title from first page headings or top text."""
        for b in blocks[:5]:
            if b.page_num == 1 and (b.is_heading or b.font_size > 14.0):
                text = b.text.split('\n')[0].strip()
                if len(text) > 5 and len(text) < 100:
                    return text

        # Clean fallback_id (e.g. 128790086-Social-Media-Strategy-Blueprint -> The Ten Step Social Media Strategy Blueprint)
        clean_name = re.sub(r'^\d+[\-_]?', '', fallback_id)
        clean_name = clean_name.replace('-', ' ').replace('_', ' ').title()
        if 'Social Media Strategy' in clean_name:
            return "The Ten Step Social Media Strategy Blueprint"
        return clean_name or "Document"

    def _match_section_heading(self, block: ExtractedBlock) -> Tuple[bool, str, str]:
        """Check if block is a Level 1 Section heading. Returns (is_match, title, remaining_text)."""
        text = block.text.strip()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines or len(lines) > 4:
            return False, "", ""

        first_line = lines[0]
        for pat in self.SECTION_PATTERNS:
            m = pat.match(first_line)
            if m:
                # E.g. "Step One — The Destination"
                title = first_line
                remaining = "\n".join(lines[1:])
                return True, self._clean_heading_title(title), remaining

        if block.is_heading and block.heading_level == 1:
            return True, self._clean_heading_title(first_line), "\n".join(lines[1:])

        return False, "", ""

    def _match_subsection_heading(self, block: ExtractedBlock) -> Tuple[bool, str, str]:
        """Check if block is a Level 2 Subsection heading. Returns (is_match, title, remaining_text)."""
        text = block.text.strip()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines or len(lines) > 4:
            return False, "", ""

        first_line = lines[0]
        for pat in self.SUBSECTION_PATTERNS:
            m = pat.match(first_line)
            if m:
                title = m.group(1) if m.groups() else first_line
                remaining = "\n".join(lines[1:])
                return True, self._clean_heading_title(title), remaining

        if block.is_heading and block.heading_level == 2:
            return True, self._clean_heading_title(first_line), "\n".join(lines[1:])

        return False, "", ""

    def _clean_heading_title(self, title: str) -> str:
        """Normalize heading title."""
        cleaned = re.sub(r'\s+', ' ', title).strip()
        cleaned = re.sub(r'^#+\s*', '', cleaned)
        return cleaned

    def _is_toc_block(self, text: str) -> bool:
        """Check if text is part of a Table of Contents."""
        lines = text.split('\n')
        toc_lines = sum(1 for line in lines if self.TOC_LINE_PATTERN.search(line) or re.search(r'^\s*Step\s+[A-Za-z0-9]+\s*\.{3,}', line, re.IGNORECASE))
        return toc_lines >= 2 or 'table of contents' in text.lower()

    def _is_bio_block(self, text: str) -> bool:
        """Check if text is part of Biography or Author info."""
        t_low = text.lower()
        return 'about the author' in t_low or 'about us' in t_low or 'about tent social' in t_low
