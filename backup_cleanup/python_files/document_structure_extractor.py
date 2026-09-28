#!/usr/bin/env python3
"""
Document Structure Extractor - Instruction 1: Preserve document structure during extraction.

Extracts pages into blocks retaining position (bbox), paragraph breaks, heading info,
and page numbers. Establishes reading order before flattening into text.
Detects garbled text and retries extraction/OCR without asking an LLM to guess wording.
Keeps original PDF and raw extraction alongside structured blocks.
"""

import os
import re
import math
import unicodedata
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ExtractedSpan:
    """Individual text span with typography details."""
    text: str
    font_name: str = ""
    font_size: float = 12.0
    is_bold: bool = False
    is_italic: bool = False
    color: int = 0
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class ExtractedBlock:
    """Structured document block with layout and typography metadata."""
    block_id: str
    page_num: int  # 1-indexed
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    text: str
    block_type: str = "paragraph"  # "heading", "paragraph", "list_item", "table", "caption", "furniture"
    font_size: float = 12.0
    is_bold: bool = False
    is_heading: bool = False
    heading_level: int = 0  # 1=H1 (Step), 2=H2 (Subsection), 3=H3
    reading_order_idx: int = 0
    spans: List[ExtractedSpan] = field(default_factory=list)
    is_garbled: bool = False
    garbled_reason: Optional[str] = None
    extraction_source: str = "pymupdf_dict"  # "pymupdf_dict", "pymupdf_blocks", "pdfplumber", "ocr_fallback"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedDocument:
    """Complete structured extraction of a document."""
    document_id: str
    source_file: str
    file_type: str
    page_count: int
    blocks: List[ExtractedBlock]
    raw_text: str
    raw_extraction: Dict[str, Any]
    extraction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    pages_with_garbled_text: List[int] = field(default_factory=list)
    recovery_attempts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "source_file": self.source_file,
            "file_type": self.file_type,
            "page_count": self.page_count,
            "extraction_timestamp": self.extraction_timestamp,
            "pages_with_garbled_text": self.pages_with_garbled_text,
            "recovery_attempts": self.recovery_attempts,
            "block_count": len(self.blocks),
            "blocks": [b.to_dict() for b in self.blocks]
        }


class GarbledTextDetector:
    """Detects corrupted, garbled, or mis-extracted text from PDFs."""

    # Patterns indicating OCR/glyph corruption
    UNMAPPED_GLYPH_PATTERN = re.compile(r'[`\^\\\[\]_~]{2,}|[0-9][a-zA-Z]`[V\^\\PSSILSLM]+')
    BROKEN_WORD_PATTERN = re.compile(r'\b[a-zA-Z]\s+[a-zA-Z]{1,2}\s+[a-zA-Z]\b|\b[a-zA-Z]\s+[a-zA-Z]{2,4}\b')
    HIGH_SYMBOL_RATIO_PATTERN = re.compile(r'[^a-zA-Z0-9\s.,!?:;\'"()/\-–—]')

    @classmethod
    def analyze_text(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Analyze text for corruption/garbling.
        Returns (is_garbled, reason).
        """
        if not text or not text.strip():
            return False, None

        cleaned = text.strip()
        total_len = len(cleaned)
        if total_len < 4:
            return False, None

        # 1. Unmapped font glyphs / binary-shifted strings (e.g. 0n the end`V\^PSSILSLM[^P[O)
        if cls.UNMAPPED_GLYPH_PATTERN.search(cleaned):
            return True, "unmapped_glyph_sequence"

        # 2. Check for replacement / control characters
        control_chars = [c for c in cleaned if unicodedata.category(c).startswith('C') and c not in '\n\r\t']
        if len(control_chars) > 0:
            return True, f"contains_{len(control_chars)}_control_chars"

        # 3. Check for broken word spacing (e.g. 'h elp' or 's o c i a l')
        broken_words = cls.BROKEN_WORD_PATTERN.findall(cleaned)
        words = cleaned.split()
        if len(words) > 3 and len(broken_words) >= max(2, len(words) // 3):
            return True, "excessive_broken_word_spacing"

        # 4. Check symbol/gibberish ratio
        symbols = cls.HIGH_SYMBOL_RATIO_PATTERN.findall(cleaned)
        if total_len > 15 and len(symbols) / total_len > 0.35:
            return True, f"high_symbol_ratio_{len(symbols)/total_len:.2f}"

        # 5. Check printable character ratio
        printable_count = sum(1 for c in cleaned if c.isprintable() or c in '\n\r\t')
        if printable_count / total_len < 0.85:
            return True, f"low_printable_ratio_{printable_count/total_len:.2f}"

        return False, None

    @classmethod
    def fix_broken_word_spacing(cls, text: str) -> str:
        """Fix isolated spaced letters like 'h elp' -> 'help' when detected."""
        # Fix single char spaces inside words: e.g., 'h elp' -> 'help'
        fixed = re.sub(r'\b([a-zA-Z])\s+([a-zA-Z]{2,})\b', r'\1\2', text)
        fixed = re.sub(r'\b([a-zA-Z]{2,})\s+([a-zA-Z])\b', r'\1\2', fixed)
        return fixed


class DocumentStructureExtractor:
    """
    Position-aware document structure extractor.
    Extracts PDF and structured text into layout-aware blocks retaining
    coordinates, reading order, headings, and page boundaries.
    """

    def __init__(self, enable_ocr: bool = True):
        self.enable_ocr = enable_ocr

    def extract_document(self, file_path: Path) -> ExtractedDocument:
        """Extract a document with full structure preservation."""
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        doc_id = file_path.stem

        if ext == '.pdf':
            return self._extract_pdf(file_path, doc_id)
        else:
            return self._extract_plain_text(file_path, doc_id)

    def _extract_pdf(self, file_path: Path, doc_id: str) -> ExtractedDocument:
        """Extract PDF with PyMuPDF layout analysis and reading order establishment."""
        blocks: List[ExtractedBlock] = []
        raw_pages: List[str] = []
        raw_extraction: Dict[str, Any] = {"pages": []}
        pages_with_garbled: List[int] = []
        recovery_attempts: List[Dict[str, Any]] = []

        try:
            import pymupdf
            doc = pymupdf.open(str(file_path))
        except ImportError:
            try:
                import fitz
                doc = fitz.open(str(file_path))
            except ImportError:
                logger.warning("PyMuPDF (fitz) not available. Falling back to text extraction.")
                return self._fallback_pdf_extract(file_path, doc_id)

        try:
            page_count = len(doc)
            global_block_idx = 0

            # Calculate document-level median font size for relative heading detection
            all_font_sizes = []

            for page_num in range(page_count):
                page = doc[page_num]
                page_dict = page.get_text("dict")
                for b in page_dict.get("blocks", []):
                    if b.get("type") == 0:  # text block
                        for line in b.get("lines", []):
                            for span in line.get("spans", []):
                                text = span.get("text", "").strip()
                                if text:
                                    all_font_sizes.append(span.get("size", 12.0))

            median_font_size = (
                sorted(all_font_sizes)[len(all_font_sizes) // 2]
                if all_font_sizes
                else 12.0
            )

            # Process each page with reading-order sorting
            for page_idx in range(page_count):
                page_num = page_idx + 1
                page = doc[page_idx]
                page_raw_text = page.get_text("text")
                raw_pages.append(page_raw_text)

                page_dict = page.get_text("dict")
                raw_extraction["pages"].append({
                    "page_num": page_num,
                    "rect": list(page.rect),
                    "block_count": len(page_dict.get("blocks", []))
                })

                # Check if raw page text is garbled
                is_garbled, garbled_reason = GarbledTextDetector.analyze_text(page_raw_text)
                if is_garbled:
                    pages_with_garbled.append(page_num)
                    # Attempt retry extraction with alternate flags
                    recovered_blocks = self._retry_extract_page(page, page_num, file_path)
                    recovery_attempts.append({
                        "page_num": page_num,
                        "initial_reason": garbled_reason,
                        "recovered": recovered_blocks is not None
                    })
                    if recovered_blocks:
                        for b in recovered_blocks:
                            b.reading_order_idx = global_block_idx
                            global_block_idx += 1
                            blocks.append(b)
                        continue

                # Normal extraction from page dict
                page_blocks = self._extract_page_blocks(
                    page, page_num, median_font_size
                )

                # Sort blocks by 2-column or 1-column reading order
                sorted_blocks = self._establish_reading_order(page_blocks, page.rect.width)

                for b in sorted_blocks:
                    b.reading_order_idx = global_block_idx
                    global_block_idx += 1
                    blocks.append(b)

            doc.close()

            raw_text = "\n\n".join(raw_pages)
            return ExtractedDocument(
                document_id=doc_id,
                source_file=str(file_path),
                file_type="pdf",
                page_count=page_count,
                blocks=blocks,
                raw_text=raw_text,
                raw_extraction=raw_extraction,
                pages_with_garbled_text=pages_with_garbled,
                recovery_attempts=recovery_attempts
            )

        except Exception as e:
            logger.error(f"Error during PyMuPDF extraction of {file_path}: {e}")
            return self._fallback_pdf_extract(file_path, doc_id)

    def _extract_page_blocks(
        self, page: Any, page_num: int, median_font_size: float
    ) -> List[ExtractedBlock]:
        """Extract structured blocks from a PyMuPDF page dict."""
        page_dict = page.get_text("dict")
        page_blocks: List[ExtractedBlock] = []

        for b_idx, b in enumerate(page_dict.get("blocks", [])):
            if b.get("type") != 0:  # Skip non-text blocks (images, drawings)
                continue

            bbox = tuple(b.get("bbox", (0.0, 0.0, 0.0, 0.0)))
            lines = b.get("lines", [])
            spans_list: List[ExtractedSpan] = []
            line_texts = []
            max_font_size = 0.0
            is_bold = False

            for line in lines:
                line_spans_text = []
                for span in line.get("spans", []):
                    stext = span.get("text", "")
                    if not stext:
                        continue
                    ssize = span.get("size", 12.0)
                    sfont = span.get("font", "")
                    sflags = span.get("flags", 0)
                    sbold = bool(sflags & 2 != 0 or "bold" in sfont.lower() or "black" in sfont.lower())
                    sitalic = bool(sflags & 1 != 0 or "italic" in sfont.lower() or "oblique" in sfont.lower())
                    scolor = span.get("color", 0)
                    sbbox = tuple(span.get("bbox", (0.0, 0.0, 0.0, 0.0)))

                    spans_list.append(ExtractedSpan(
                        text=stext,
                        font_name=sfont,
                        font_size=ssize,
                        is_bold=sbold,
                        is_italic=sitalic,
                        color=scolor,
                        bbox=sbbox
                    ))
                    line_spans_text.append(stext)
                    if ssize > max_font_size:
                        max_font_size = ssize
                    if sbold:
                        is_bold = True

                if line_spans_text:
                    line_texts.append("".join(line_spans_text))

            block_text = "\n".join(line_texts).strip()
            if not block_text:
                continue

            # Check if block is garbled
            is_garbled, garbled_reason = GarbledTextDetector.analyze_text(block_text)
            if is_garbled:
                # Try soft spacing fix
                fixed_text = GarbledTextDetector.fix_broken_word_spacing(block_text)
                is_still_garbled, _ = GarbledTextDetector.analyze_text(fixed_text)
                if not is_still_garbled:
                    block_text = fixed_text
                    is_garbled = False
                    garbled_reason = None

            # Detect heading status
            is_heading, heading_level = self._classify_heading(
                block_text, max_font_size, median_font_size, is_bold
            )

            block_type = "heading" if is_heading else "paragraph"
            if re.match(r'^\s*(\d+[\.\)]|[\u2022\u2023\u25E6\u2043\u2219\-*])\s+', block_text):
                block_type = "list_item"

            block_id = f"p{page_num:03d}_b{b_idx:03d}"
            page_blocks.append(ExtractedBlock(
                block_id=block_id,
                page_num=page_num,
                bbox=bbox,
                text=block_text,
                block_type=block_type,
                font_size=max_font_size if max_font_size > 0 else median_font_size,
                is_bold=is_bold,
                is_heading=is_heading,
                heading_level=heading_level,
                spans=spans_list,
                is_garbled=is_garbled,
                garbled_reason=garbled_reason,
                extraction_source="pymupdf_dict"
            ))

        return page_blocks

    def _classify_heading(
        self, text: str, font_size: float, median_font_size: float, is_bold: bool
    ) -> Tuple[bool, int]:
        """Classify if block text represents a heading and determine level."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines or len(lines) > 4:
            # Long paragraphs are not headings
            return False, 0

        first_line = lines[0]
        # Major step patterns: Step One, Step 1, Step Two - The Destination, Chapter 1
        step_match = re.match(r'^(Step\s+(?:[0-9]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)|Chapter\s+[0-9]+)', first_line, re.IGNORECASE)
        if step_match:
            return True, 1

        # Font size checks
        is_large_font = font_size >= median_font_size * 1.25
        is_medium_font = font_size >= median_font_size * 1.10

        # Known structural subsection titles
        subsection_keywords = [
            'four tips for goal setting', 'tools & resources', 'tools and resources',
            'checklist', 'action items', 'key takeaways', 'summary', 'overview',
            'the destination', 'the audience', 'content strategy', 'execution plan'
        ]
        text_lower = text.lower().strip()
        for kw in subsection_keywords:
            if kw in text_lower and len(text_lower) < 80:
                return True, 2

        # Numbered tips: e.g. "Tip 1:", "1. Make It Medium To Long Term"
        tip_match = re.match(r'^(?:Tip\s+\d+|[1-4]\.\s+[A-Z])', first_line)
        if tip_match and len(text) < 100:
            return True, 2

        if is_large_font and len(text) < 120:
            return True, 1
        elif (is_medium_font or is_bold) and len(text) < 100 and not text.endswith('.'):
            return True, 2

        return False, 0

    def _establish_reading_order(
        self, blocks: List[ExtractedBlock], page_width: float
    ) -> List[ExtractedBlock]:
        """
        Sort blocks into natural reading order.
        Handles both single-column and multi-column layouts by detecting column gutters.
        """
        if len(blocks) <= 1:
            return blocks

        # Check if page layout is multi-column (e.g. 2-column)
        midpoint = page_width / 2.0
        left_blocks = []
        right_blocks = []
        spanning_blocks = []

        for b in blocks:
            x0, y0, x1, y1 = b.bbox
            width = x1 - x0
            if width > page_width * 0.70:
                spanning_blocks.append(b)
            elif x1 <= midpoint + 20:
                left_blocks.append(b)
            elif x0 >= midpoint - 20:
                right_blocks.append(b)
            else:
                spanning_blocks.append(b)

        # If significant blocks exist in both left and right columns
        if len(left_blocks) >= 2 and len(right_blocks) >= 2:
            # 2-column layout: sort spanning blocks by y0, and column blocks within their vertical bands
            all_sorted: List[ExtractedBlock] = []
            left_blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
            right_blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
            spanning_blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))

            combined = []
            combined.extend(spanning_blocks)
            combined.extend(left_blocks)
            combined.extend(right_blocks)
            combined.sort(key=lambda b: (
                0 if b in spanning_blocks else (1 if b in left_blocks else 2),
                b.bbox[1]
            ))
            return combined

        # Single column layout: sort primarily by top-to-bottom (y0), then left-to-right (x0)
        return sorted(blocks, key=lambda b: (round(b.bbox[1] / 5.0) * 5.0, b.bbox[0]))

    def _retry_extract_page(
        self, page: Any, page_num: int, file_path: Path
    ) -> Optional[List[ExtractedBlock]]:
        """
        Retry extraction of a garbled page using alternate layout parameters or OCR.
        Never guesses words with an LLM.
        """
        logger.info(f"Retrying extraction for garbled page {page_num} of {file_path.name}")

        # Attempt 1: Raw text with dehyphenation flags
        try:
            import pymupdf
            flags = pymupdf.TEXT_DEHYPHENATE | pymupdf.TEXT_PRESERVE_SPANS
            blocks_raw = page.get_text("blocks", flags=flags)
            recovered = []
            for idx, b in enumerate(blocks_raw):
                btext = b[4].strip()
                if not btext:
                    continue
                bbox = (b[0], b[1], b[2], b[3])
                is_garbled, reason = GarbledTextDetector.analyze_text(btext)
                if not is_garbled:
                    recovered.append(ExtractedBlock(
                        block_id=f"p{page_num:03d}_rec_{idx:03d}",
                        page_num=page_num,
                        bbox=bbox,
                        text=btext,
                        block_type="paragraph",
                        font_size=12.0,
                        is_bold=False,
                        is_heading=False,
                        extraction_source="pymupdf_dehyphenate"
                    ))
            if recovered:
                return recovered
        except Exception as e:
            logger.debug(f"Dehyphenate retry failed on page {page_num}: {e}")

        # Attempt 2: pdfplumber extraction if available
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                if page_num - 1 < len(pdf.pages):
                    plumber_page = pdf.pages[page_num - 1]
                    ptext = plumber_page.extract_text(layout=True)
                    if ptext and ptext.strip():
                        is_garbled, _ = GarbledTextDetector.analyze_text(ptext)
                        if not is_garbled:
                            return [ExtractedBlock(
                                block_id=f"p{page_num:03d}_plumber_001",
                                page_num=page_num,
                                bbox=(0.0, 0.0, float(plumber_page.width), float(plumber_page.height)),
                                text=ptext.strip(),
                                block_type="paragraph",
                                extraction_source="pdfplumber"
                            )]
        except Exception as e:
            logger.debug(f"pdfplumber retry failed on page {page_num}: {e}")

        # Attempt 3: OCR via pytesseract if available and enabled
        if self.enable_ocr:
            try:
                import pytesseract
                from PIL import Image
                import io

                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img)
                if ocr_text and ocr_text.strip():
                    is_garbled, _ = GarbledTextDetector.analyze_text(ocr_text)
                    if not is_garbled:
                        return [ExtractedBlock(
                            block_id=f"p{page_num:03d}_ocr_001",
                            page_num=page_num,
                            bbox=(0.0, 0.0, float(page.rect.width), float(page.rect.height)),
                            text=ocr_text.strip(),
                            block_type="paragraph",
                            extraction_source="ocr_pytesseract"
                        )]
            except Exception as e:
                logger.debug(f"OCR retry failed on page {page_num}: {e}")

        return None

    def _fallback_pdf_extract(self, file_path: Path, doc_id: str) -> ExtractedDocument:
        """Fallback extraction for environments without PyMuPDF."""
        blocks: List[ExtractedBlock] = []
        raw_text = ""

        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1
                    text = page.extract_text() or ""
                    raw_text += text + "\n\n"
                    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                    for b_idx, p in enumerate(paragraphs):
                        blocks.append(ExtractedBlock(
                            block_id=f"p{page_num:03d}_b{b_idx:03d}",
                            page_num=page_num,
                            bbox=(0.0, 0.0, float(page.width), float(page.height)),
                            text=p,
                            block_type="paragraph",
                            reading_order_idx=len(blocks),
                            extraction_source="pdfplumber_fallback"
                        ))
                return ExtractedDocument(
                    document_id=doc_id,
                    source_file=str(file_path),
                    file_type="pdf",
                    page_count=len(pdf.pages),
                    blocks=blocks,
                    raw_text=raw_text,
                    raw_extraction={}
                )
        except Exception as e:
            logger.error(f"Fallback PDF extraction failed: {e}")

        return ExtractedDocument(
            document_id=doc_id,
            source_file=str(file_path),
            file_type="pdf",
            page_count=0,
            blocks=[],
            raw_text="",
            raw_extraction={}
        )

    def _extract_plain_text(self, file_path: Path, doc_id: str) -> ExtractedDocument:
        """Extract structured blocks from Markdown or plain text files."""
        blocks: List[ExtractedBlock] = []
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            raw_text = f.read()

        paragraphs = [p.strip() for p in raw_text.split('\n\n') if p.strip()]
        for idx, p in enumerate(paragraphs):
            is_heading = False
            heading_level = 0
            if p.startswith('#'):
                level = len(p) - len(p.lstrip('#'))
                is_heading = True
                heading_level = min(level, 3)
            elif re.match(r'^(Step\s+[0-9A-Za-z]+|Chapter\s+[0-9]+)', p, re.IGNORECASE):
                is_heading = True
                heading_level = 1

            blocks.append(ExtractedBlock(
                block_id=f"txt_b{idx:03d}",
                page_num=1,
                bbox=(0.0, float(idx * 50), 600.0, float((idx + 1) * 50)),
                text=p,
                block_type="heading" if is_heading else "paragraph",
                font_size=16.0 if is_heading else 12.0,
                is_bold=is_heading,
                is_heading=is_heading,
                heading_level=heading_level,
                reading_order_idx=idx,
                extraction_source="text_file"
            ))

        return ExtractedDocument(
            document_id=doc_id,
            source_file=str(file_path),
            file_type=file_path.suffix.lstrip('.'),
            page_count=1,
            blocks=blocks,
            raw_text=raw_text,
            raw_extraction={}
        )
