#!/usr/bin/env python3
"""
Structure-Aware Semantic Chunker - Instruction 4: Chunk within sections using complete paragraphs and sentences.

Applies structure-first chunking:
- Target size: ~500 tokens
- Maximum size: 800 tokens (including heading context prefix)
- Small chunks: Kept if self-contained; merged with sibling paragraphs in the same subsection
- Splitting order: Subsection → paragraph → sentence → token fallback
- Overlap: None for complete subsections; 1 preceding sentence for split continuations
- Cross-section overlap: Strictly DISABLED
- Measures tokens using tiktoken (cl100k_base / o200k_base) with reliable fallback
- Keeps tip labels together with their explanations
- Keeps manageable numbered lists together (e.g. four goal-setting tips)
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from document_structure_extractor import ExtractedBlock
from section_hierarchy_builder import SectionNode, DocumentHierarchy

logger = logging.getLogger(__name__)


# Initialize Tokenizer with tiktoken
class TokenCounter:
    """Accurate token counter using tiktoken with fallback."""

    def __init__(self, model_encoding: str = "cl100k_base"):
        self.encoding_name = model_encoding
        self.encoder = None
        try:
            import tiktoken
            self.encoder = tiktoken.get_encoding(model_encoding)
        except Exception as e:
            logger.debug(f"tiktoken not available ({e}), using word-ratio estimation.")

    def count_tokens(self, text: str) -> int:
        """Count tokens in string."""
        if not text:
            return 0
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception:
                pass
        # Fallback estimation: ~0.75 words per token (1.3 tokens per word)
        words = len(text.split())
        return max(1, int(words * 1.33))


@dataclass
class StructuredChunk:
    """Complete semantic chunk with structural lineage and metadata."""
    chunk_id: str
    document_id: str
    document_version: str
    section_path: str
    parent_section_id: Optional[str]
    chunk_index: int
    source_text: str  # Clean original body text
    embedding_text: str  # Contextualized text with heading prefix
    token_count: int
    page_start: Optional[int]
    page_end: Optional[int]
    quality_flags: List[str] = field(default_factory=list)
    source_block_ids: List[str] = field(default_factory=list)
    has_continuation: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StructuredChunker:
    """
    Chunks document trees respecting section boundaries,
    preserving tip labels and numbered lists, and adhering to strict token budgets.
    """

    def __init__(
        self,
        target_tokens: int = 500,
        max_tokens: int = 800,
        min_tokens: int = 40,
        token_counter: Optional[TokenCounter] = None,
        tokenizer_model: str = "cl100k_base"
    ):
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.token_counter = token_counter or TokenCounter(tokenizer_model)

    def chunk_hierarchy(
        self, hierarchy: DocumentHierarchy, document_version: str = "1.0"
    ) -> List[StructuredChunk]:
        """Produce semantic chunks from document hierarchy."""
        all_chunks: List[StructuredChunk] = []
        global_chunk_idx = 0

        # Traverse sections starting from level 1 / level 2 nodes
        sections_to_process = self._collect_leaf_sections(hierarchy.root)

        for sec in sections_to_process:
            sec_chunks = self._chunk_section(sec, hierarchy.document_id, document_version, global_chunk_idx)
            for c in sec_chunks:
                c.chunk_index = global_chunk_idx
                global_chunk_idx += 1
                all_chunks.append(c)

        return all_chunks

    def _collect_leaf_sections(self, root: SectionNode) -> List[SectionNode]:
        """Collect sections/subsections that contain content blocks."""
        leaves: List[SectionNode] = []

        def traverse(node: SectionNode):
            # If node has blocks directly, or if it is a leaf
            if node.blocks:
                leaves.append(node)
            for child in node.children:
                traverse(child)

        traverse(root)
        return leaves

    def _chunk_section(
        self,
        section: SectionNode,
        document_id: str,
        document_version: str,
        start_index: int
    ) -> List[StructuredChunk]:
        """Chunk an individual section without bleeding across boundaries."""
        chunks: List[StructuredChunk] = []
        if not section.blocks:
            return chunks

        # Prepare heading prefix
        heading_prefix = self._build_heading_prefix(section.section_path)
        prefix_tokens = self.token_counter.count_tokens(heading_prefix)
        available_max_tokens = max(100, self.max_tokens - prefix_tokens)

        # Merge blocks into logical paragraphs / units, keeping tip labels with explanations
        logical_units = self._group_blocks_into_units(section.blocks)

        # Attempt 1: Subsection level - if entire subsection fits in max tokens, keep as 1 chunk!
        full_section_text = "\n\n".join(u['text'] for u in logical_units)
        full_tokens = self.token_counter.count_tokens(full_section_text)

        if full_tokens <= available_max_tokens and full_tokens >= self.min_tokens:
            page_start = min(u['page_num'] for u in logical_units)
            page_end = max(u['page_num'] for u in logical_units)
            block_ids = [bid for u in logical_units for bid in u['block_ids']]
            emb_text = f"{heading_prefix}\n\n{full_section_text}".strip()

            flags = list(section.quality_flags)
            if "clean" not in flags and not any(f.startswith("is_") for f in flags):
                flags.append("clean")
            flags.append("complete_subsection")

            chunk_id = f"{section.section_id}_c001"
            chunks.append(StructuredChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                document_version=document_version,
                section_path=section.section_path,
                parent_section_id=section.parent_id,
                chunk_index=start_index,
                source_text=full_section_text,
                embedding_text=emb_text,
                token_count=self.token_counter.count_tokens(emb_text),
                page_start=page_start,
                page_end=page_end,
                quality_flags=flags,
                source_block_ids=block_ids,
                has_continuation=False
            ))
            return chunks

        # Attempt 2: Paragraph / Logical Unit chunking with complete sentence splitting
        current_unit_texts: List[str] = []
        current_block_ids: List[str] = []
        current_pages: List[int] = []
        current_tokens = 0
        chunk_sub_idx = 1
        previous_last_sentence: Optional[str] = None

        for unit in logical_units:
            unit_text = unit['text']
            unit_tokens = self.token_counter.count_tokens(unit_text)

            # If unit itself is larger than available_max_tokens, split it by sentences
            if unit_tokens > available_max_tokens:
                # Flush pending chunk if any
                if current_unit_texts:
                    body = "\n\n".join(current_unit_texts)
                    emb = f"{heading_prefix}\n\n{body}".strip()
                    c_id = f"{section.section_id}_c{chunk_sub_idx:03d}"
                    chunk_sub_idx += 1
                    chunks.append(StructuredChunk(
                        chunk_id=c_id,
                        document_id=document_id,
                        document_version=document_version,
                        section_path=section.section_path,
                        parent_section_id=section.parent_id,
                        chunk_index=start_index + len(chunks),
                        source_text=body,
                        embedding_text=emb,
                        token_count=self.token_counter.count_tokens(emb),
                        page_start=min(current_pages) if current_pages else section.page_start,
                        page_end=max(current_pages) if current_pages else section.page_end,
                        quality_flags=list(section.quality_flags) + ["clean"],
                        source_block_ids=list(current_block_ids),
                        has_continuation=False
                    ))
                    current_unit_texts = []
                    current_block_ids = []
                    current_pages = []
                    current_tokens = 0

                # Split large unit by sentences with 1 preceding sentence overlap for continuations
                unit_sentence_chunks = self._split_unit_by_sentences(
                    unit, available_max_tokens, heading_prefix, section, document_id, document_version
                )
                for sc in unit_sentence_chunks:
                    sc.chunk_id = f"{section.section_id}_c{chunk_sub_idx:03d}"
                    chunk_sub_idx += 1
                    sc.chunk_index = start_index + len(chunks)
                    chunks.append(sc)
                continue

            # Check if adding this unit exceeds target or max tokens
            if current_tokens + unit_tokens > available_max_tokens and current_unit_texts:
                # Finalize current chunk
                body = "\n\n".join(current_unit_texts)
                emb = f"{heading_prefix}\n\n{body}".strip()
                c_id = f"{section.section_id}_c{chunk_sub_idx:03d}"
                chunk_sub_idx += 1
                chunks.append(StructuredChunk(
                    chunk_id=c_id,
                    document_id=document_id,
                    document_version=document_version,
                    section_path=section.section_path,
                    parent_section_id=section.parent_id,
                    chunk_index=start_index + len(chunks),
                    source_text=body,
                    embedding_text=emb,
                    token_count=self.token_counter.count_tokens(emb),
                    page_start=min(current_pages) if current_pages else section.page_start,
                    page_end=max(current_pages) if current_pages else section.page_end,
                    quality_flags=list(section.quality_flags) + ["clean"],
                    source_block_ids=list(current_block_ids),
                    has_continuation=False
                ))
                current_unit_texts = []
                current_block_ids = []
                current_pages = []
                current_tokens = 0

            # Add unit to current chunk
            current_unit_texts.append(unit_text)
            current_block_ids.extend(unit['block_ids'])
            current_pages.append(unit['page_num'])
            current_tokens += unit_tokens

        # Flush final chunk in section
        if current_unit_texts:
            body = "\n\n".join(current_unit_texts)
            emb = f"{heading_prefix}\n\n{body}".strip()
            c_id = f"{section.section_id}_c{chunk_sub_idx:03d}"
            chunks.append(StructuredChunk(
                chunk_id=c_id,
                document_id=document_id,
                document_version=document_version,
                section_path=section.section_path,
                parent_section_id=section.parent_id,
                chunk_index=start_index + len(chunks),
                source_text=body,
                embedding_text=emb,
                token_count=self.token_counter.count_tokens(emb),
                page_start=min(current_pages) if current_pages else section.page_start,
                page_end=max(current_pages) if current_pages else section.page_end,
                quality_flags=list(section.quality_flags) + ["clean"],
                source_block_ids=list(current_block_ids),
                has_continuation=False
            ))

        return chunks

    def _group_blocks_into_units(self, blocks: List[ExtractedBlock]) -> List[Dict[str, Any]]:
        """
        Group blocks so that tip labels, subheadings, and list items stay
        with their explaining paragraphs.
        """
        units: List[Dict[str, Any]] = []
        i = 0
        while i < len(blocks):
            b = blocks[i]
            text = b.text.strip()
            if not text:
                i += 1
                continue

            # Check if block is a tip label or standalone subheading (e.g. "Tip 1: Make It Medium To Long Term")
            is_label = self._is_label_or_tip_header(text)
            if is_label and i + 1 < len(blocks):
                # Fuse with subsequent explanation block!
                next_b = blocks[i + 1]
                fused_text = f"{text}\n{next_b.text.strip()}"
                units.append({
                    "text": fused_text,
                    "block_ids": [b.block_id, next_b.block_id],
                    "page_num": b.page_num
                })
                i += 2
                continue

            units.append({
                "text": text,
                "block_ids": [b.block_id],
                "page_num": b.page_num
            })
            i += 1

        return units

    def _is_label_or_tip_header(self, text: str) -> bool:
        """Check if text is a label/title meant to describe the next paragraph."""
        lines = text.split('\n')
        if len(lines) > 2:
            return False
        first_line = lines[0].strip()
        if re.match(r'^(?:Tip\s+\d+|[1-4]\.\s+[A-Z]|Step\s+[0-9A-Za-z]+)', first_line):
            return True
        if len(text) < 60 and not text.endswith('.'):
            return True
        return False

    def _split_unit_by_sentences(
        self,
        unit: Dict[str, Any],
        max_tokens: int,
        heading_prefix: str,
        section: SectionNode,
        document_id: str,
        document_version: str
    ) -> List[StructuredChunk]:
        """Split a large unit along sentence boundaries with 1 sentence overlap for continuations."""
        sentences = self._split_sentences(unit['text'])
        chunks: List[StructuredChunk] = []

        cur_sentences: List[str] = []
        cur_tokens = 0
        overlap_sentence: Optional[str] = None

        for sent in sentences:
            sent_tokens = self.token_counter.count_tokens(sent)
            if cur_tokens + sent_tokens > max_tokens and cur_sentences:
                body = " ".join(cur_sentences)
                emb = f"{heading_prefix}\n\n{body}".strip()
                chunks.append(StructuredChunk(
                    chunk_id="",
                    document_id=document_id,
                    document_version=document_version,
                    section_path=section.section_path,
                    parent_section_id=section.parent_id,
                    chunk_index=0,
                    source_text=body,
                    embedding_text=emb,
                    token_count=self.token_counter.count_tokens(emb),
                    page_start=unit['page_num'],
                    page_end=unit['page_num'],
                    quality_flags=list(section.quality_flags) + ["has_continuation"],
                    source_block_ids=list(unit['block_ids']),
                    has_continuation=True
                ))
                # Overlap: 1 preceding sentence for split continuation
                overlap_sentence = cur_sentences[-1] if len(cur_sentences) > 1 else None
                cur_sentences = [overlap_sentence] if overlap_sentence else []
                cur_tokens = self.token_counter.count_tokens(overlap_sentence) if overlap_sentence else 0

            cur_sentences.append(sent)
            cur_tokens += sent_tokens

        if cur_sentences:
            body = " ".join(cur_sentences)
            emb = f"{heading_prefix}\n\n{body}".strip()
            chunks.append(StructuredChunk(
                chunk_id="",
                document_id=document_id,
                document_version=document_version,
                section_path=section.section_path,
                parent_section_id=section.parent_id,
                chunk_index=0,
                source_text=body,
                embedding_text=emb,
                token_count=self.token_counter.count_tokens(emb),
                page_start=unit['page_num'],
                page_end=unit['page_num'],
                quality_flags=list(section.quality_flags),
                source_block_ids=list(unit['block_ids']),
                has_continuation=False
            ))

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text cleanly into sentences."""
        # Simple sentence splitter preserving abbreviations
        pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _build_heading_prefix(self, section_path: str) -> str:
        """
        Build heading context prefix from section_path:
        Document: ...
        Section: ...
        Subsection: ...
        """
        parts = [p.strip() for p in section_path.split(' > ') if p.strip()]
        lines = []
        if len(parts) >= 1:
            lines.append(f"Document: {parts[0]}")
        if len(parts) >= 2:
            lines.append(f"Section: {parts[1]}")
        if len(parts) >= 3:
            lines.append(f"Subsection: {parts[2]}")
        return "\n".join(lines)
