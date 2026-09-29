#!/usr/bin/env python3
"""
Comprehensive Unit & Integration Test Suite for the 7 Pipeline Instructions:
1. Preserve document structure during extraction
2. Clean repeated page furniture without deleting useful content
3. Build section hierarchy before creating chunks
4. Chunk within sections using complete paragraphs and sentences
5. Give every chunk enough context to stand alone
6. Add validation before embedding
7. Compare retrieval before and after
"""

import os
import sys
import json
import unittest
from pathlib import Path

# Add python_files to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python_files"))

from document_structure_extractor import (
    DocumentStructureExtractor,
    ExtractedBlock,
    ExtractedDocument,
    GarbledTextDetector
)
from furniture_cleaner import FurnitureCleaner, AuditEntry, CleaningResult
from section_hierarchy_builder import SectionHierarchyBuilder, SectionNode, DocumentHierarchy
from structured_chunker import StructuredChunker, TokenCounter, StructuredChunk
from chunk_context_formatter import ChunkContextFormatter, ExportableChunk
from chunk_validator import ChunkValidator, DocumentStoreDeduplicator, ValidationReport
from retrieval_evaluator import RetrievalBenchmarkEvaluator, RetrievalEngine


class TestInstruction1_PreserveDocumentStructure(unittest.TestCase):
    """Test Instruction 1: Preserve document structure during extraction."""

    def test_garbled_text_detection(self):
        # 1. Unmapped glyph sequence
        is_garbled, reason = GarbledTextDetector.analyze_text("0n the end`V\\^PSSILSLM[^P[O")
        self.assertTrue(is_garbled)
        self.assertEqual(reason, "unmapped_glyph_sequence")

        # 2. Clean text
        is_garbled, _ = GarbledTextDetector.analyze_text("This is clean, high quality text for social media strategy.")
        self.assertFalse(is_garbled)

        # 3. Broken word spacing detection & fixing
        broken = "h elp your brand grow with expert advice"
        fixed = GarbledTextDetector.fix_broken_word_spacing(broken)
        self.assertIn("help", fixed)

    def test_block_extraction_and_reading_order(self):
        extractor = DocumentStructureExtractor()
        # Create a sample markdown file
        sample_path = Path("/tmp/sample_doc.md")
        sample_path.write_text("# Step One: The Destination\n\nSetting goals is the foundation.\n\n## Four Tips for Goal Setting\n\n1. Make It Medium To Long Term.")
        try:
            doc = extractor.extract_document(sample_path)
            self.assertEqual(doc.document_id, "sample_doc")
            self.assertGreater(len(doc.blocks), 0)
            # Check reading order
            for i, b in enumerate(doc.blocks):
                self.assertEqual(b.reading_order_idx, i)
        finally:
            if sample_path.exists():
                sample_path.unlink()


class TestInstruction2_CleanPageFurniture(unittest.TestCase):
    """Test Instruction 2: Clean repeated page furniture without deleting useful content."""

    def setUp(self):
        self.cleaner = FurnitureCleaner()

    def test_repeated_running_header_and_page_number_removal(self):
        blocks = [
            ExtractedBlock(
                block_id="b01", page_num=1, bbox=(50, 20, 500, 40),
                text="Tent Social Marketing Strategy Series"
            ),
            ExtractedBlock(
                block_id="b02", page_num=1, bbox=(50, 100, 500, 300),
                text="Step One — The Destination\nGoal setting is crucial."
            ),
            ExtractedBlock(
                block_id="b03", page_num=1, bbox=(250, 750, 350, 770),
                text="Page 1"
            ),
            ExtractedBlock(
                block_id="b04", page_num=2, bbox=(50, 20, 500, 40),
                text="Tent Social Marketing Strategy Series"
            ),
            ExtractedBlock(
                block_id="b05", page_num=2, bbox=(50, 100, 500, 300),
                text="Four Tips for Goal Setting:\n1. Make It Medium To Long Term."
            ),
            ExtractedBlock(
                block_id="b06", page_num=2, bbox=(250, 750, 350, 770),
                text="Page 2"
            )
        ]
        doc = ExtractedDocument(
            document_id="test_doc", source_file="test.pdf", file_type="pdf",
            page_count=2, blocks=blocks, raw_text="", raw_extraction={}
        )

        result = self.cleaner.clean_document(doc)
        # Should remove the 2 running headers and 2 page numbers
        self.assertEqual(len(result.removed_blocks), 4)
        self.assertEqual(len(result.cleaned_blocks), 2)
        # Verify audit log is populated
        self.assertEqual(len(result.audit_log), 4)

    def test_special_section_tagging(self):
        blocks = [
            ExtractedBlock(
                block_id="b_bio", page_num=1, bbox=(50, 100, 500, 200),
                text="About Tent Social: Tent Social is a boutique social media marketing agency."
            ),
            ExtractedBlock(
                block_id="b_toc", page_num=1, bbox=(50, 250, 500, 400),
                text="Table of Contents\nStep One: The Destination . . . . 3\nStep Two: The Audience . . . . 8"
            ),
            ExtractedBlock(
                block_id="b_promo", page_num=1, bbox=(50, 450, 500, 600),
                text="Visit our website at https://tentsocial.com to subscribe to our newsletter for a special offer."
            )
        ]
        doc = ExtractedDocument(
            document_id="test_doc", source_file="test.pdf", file_type="pdf",
            page_count=1, blocks=blocks, raw_text="", raw_extraction={}
        )
        result = self.cleaner.clean_document(doc)
        self.assertIn("b_bio", result.tagged_sections["biography"])
        self.assertIn("b_toc", result.tagged_sections["toc"])
        self.assertIn("b_promo", result.tagged_sections["promotional"])


class TestInstruction3_SectionHierarchy(unittest.TestCase):
    """Test Instruction 3: Build a section hierarchy before creating chunks."""

    def test_first_section_heading_is_not_used_as_document_title(self):
        body = "Set clear goals and write them down. Review them weekly so small steps compound over time."
        blocks = [
            ExtractedBlock(block_id="h1", page_num=1, bbox=(50, 50, 500, 80),
                           text="Chapter 1: Goals", is_heading=True, heading_level=1, font_size=20.0),
            ExtractedBlock(block_id="p1", page_num=1, bbox=(50, 100, 500, 200), text=body),
            ExtractedBlock(block_id="h2", page_num=2, bbox=(50, 50, 500, 80),
                           text="Chapter 2: Audience", is_heading=True, heading_level=1, font_size=20.0),
            ExtractedBlock(block_id="p2", page_num=2, bbox=(50, 100, 500, 200), text=body),
        ]
        hierarchy = SectionHierarchyBuilder().build_hierarchy(blocks, "goals_guide")
        self.assertEqual(hierarchy.document_title, "Goals Guide")
        self.assertEqual([c.section_path for c in hierarchy.root.children],
                         ["Goals Guide > Chapter 1: Goals", "Goals Guide > Chapter 2: Audience"])

    def test_real_title_page_is_still_used_as_document_title(self):
        blocks = [
            ExtractedBlock(block_id="t", page_num=1, bbox=(50, 50, 500, 90),
                           text="Marketing Strategy Handbook", is_heading=True, heading_level=1, font_size=28.0),
            ExtractedBlock(block_id="a", page_num=1, bbox=(50, 120, 500, 140), text="By The Team"),
            ExtractedBlock(block_id="h", page_num=2, bbox=(50, 50, 500, 80),
                           text="Chapter 1: Goals", is_heading=True, heading_level=1, font_size=20.0),
        ]
        hierarchy = SectionHierarchyBuilder().build_hierarchy(blocks, "handbook")
        self.assertEqual(hierarchy.document_title, "Marketing Strategy Handbook")

    def test_hierarchy_tree_and_parent_inheritance(self):
        builder = SectionHierarchyBuilder(default_document_title="The Ten Step Social Media Strategy Blueprint")
        blocks = [
            ExtractedBlock(
                block_id="b1", page_num=2, bbox=(50, 50, 500, 80),
                text="Step One — The Destination", is_heading=True, heading_level=1
            ),
            ExtractedBlock(
                block_id="b2", page_num=2, bbox=(50, 90, 500, 150),
                text="Setting clear goals is essential for building brand equity."
            ),
            ExtractedBlock(
                block_id="b3", page_num=3, bbox=(50, 50, 500, 80),
                text="Four Tips for Goal Setting", is_heading=True, heading_level=2
            ),
            ExtractedBlock(
                block_id="b4", page_num=3, bbox=(50, 90, 500, 250),
                text="1. Make It Medium To Long Term: 12-24 months.\n2. Balance Financial & Non-Financial Goals.\n3. Be Realistic.\n4. Prioritize Key Metrics."
            ),
            ExtractedBlock(
                block_id="b5", page_num=4, bbox=(50, 50, 500, 80),
                text="Tools & Resources", is_heading=True, heading_level=2
            ),
            ExtractedBlock(
                block_id="b6", page_num=4, bbox=(50, 90, 500, 150),
                text="Recommended goal tracking software: Google Analytics."
            ),
            ExtractedBlock(
                block_id="b7", page_num=5, bbox=(50, 50, 500, 80),
                text="Step Two — The Audience", is_heading=True, heading_level=1
            ),
            ExtractedBlock(
                block_id="b8", page_num=5, bbox=(50, 90, 500, 200),
                text="Building customer personas allows focused targeting."
            )
        ]

        hierarchy = builder.build_hierarchy(blocks, "blueprint_01")
        self.assertEqual(hierarchy.document_title, "The Ten Step Social Media Strategy Blueprint")

        # Verify Step One and Step Two are Level 1 sections
        step_nodes = [c for c in hierarchy.root.children if c.level == 1 and "Step" in c.title]
        self.assertEqual(len(step_nodes), 2)
        step1, step2 = step_nodes[0], step_nodes[1]
        self.assertIn("Step One", step1.title)
        self.assertIn("Step Two", step2.title)

        # Verify Tools & Resources inherits parent Step One section path
        tools_sub = [c for c in step1.children if "Tools & Resources" in c.title]
        self.assertEqual(len(tools_sub), 1)
        self.assertEqual(
            tools_sub[0].section_path,
            "The Ten Step Social Media Strategy Blueprint > Step One — The Destination > Tools & Resources"
        )


class TestInstruction4_StructuredChunker(unittest.TestCase):
    """Test Instruction 4: Chunk within sections using complete paragraphs and sentences."""

    def test_chunk_size_limits_and_list_preservation(self):
        builder = SectionHierarchyBuilder(default_document_title="The Ten Step Social Media Strategy Blueprint")
        blocks = [
            ExtractedBlock(
                block_id="b1", page_num=3, bbox=(50, 50, 500, 80),
                text="Step One — The Destination", is_heading=True, heading_level=1
            ),
            ExtractedBlock(
                block_id="b2", page_num=3, bbox=(50, 100, 500, 130),
                text="Four Tips for Goal Setting", is_heading=True, heading_level=2
            ),
            # Tip label
            ExtractedBlock(
                block_id="b3", page_num=4, bbox=(50, 140, 500, 160),
                text="Tip 1: Make It Medium To Long Term"
            ),
            # Explanation
            ExtractedBlock(
                block_id="b4", page_num=4, bbox=(50, 170, 500, 250),
                text="Establish goals that span 12 to 24 months to create sustainable social media brand equity."
            ),
            ExtractedBlock(
                block_id="b5", page_num=4, bbox=(50, 260, 500, 350),
                text="2. Balance Financial and Non-Financial Goals: Track revenue alongside awareness and customer satisfaction."
            ),
            ExtractedBlock(
                block_id="b6", page_num=4, bbox=(50, 360, 500, 420),
                text="3. Be Realistic: Align targets with current team capacity and budget."
            ),
            ExtractedBlock(
                block_id="b7", page_num=4, bbox=(50, 430, 500, 490),
                text="4. Prioritize Key Metrics: Focus on conversion rate and high-value interactions."
            )
        ]

        hierarchy = builder.build_hierarchy(blocks, "blueprint_01")
        chunker = StructuredChunker(target_tokens=500, max_tokens=800)
        chunks = chunker.chunk_hierarchy(hierarchy)

        # All four tips should remain together in 1 complete chunk because total tokens < 800
        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        self.assertLessEqual(chunk.token_count, 800)
        self.assertIn("Make It Medium To Long Term", chunk.source_text)
        self.assertIn("Balance Financial and Non-Financial Goals", chunk.source_text)
        self.assertIn("Be Realistic", chunk.source_text)
        self.assertIn("Prioritize Key Metrics", chunk.source_text)


class TestInstruction5_StandaloneContextAndMetadata(unittest.TestCase):
    """Test Instruction 5: Give every chunk enough context to stand alone."""

    def test_heading_prefix_and_metadata_schema(self):
        chunk = StructuredChunk(
            chunk_id="chk_001",
            document_id="Social_Media_Strategy_Blueprint",
            document_version="1.0",
            section_path="The Ten Step Social Media Strategy Blueprint > Step One — The Destination > Four Tips for Goal Setting",
            parent_section_id="sec_01",
            chunk_index=0,
            source_text="Four Tips for Goal Setting:\n1. Make It Medium To Long Term.\n2. Balance Financial Goals.",
            embedding_text="Document: The Ten Step Social Media Strategy Blueprint\nSection: Step One — The Destination\nSubsection: Four Tips for Goal Setting\n\nFour Tips for Goal Setting:\n1. Make It Medium To Long Term.\n2. Balance Financial Goals.",
            token_count=75,
            page_start=4,
            page_end=5,
            quality_flags=["clean", "complete_subsection"]
        )

        formatted = ChunkContextFormatter.format_chunk(chunk)
        d = formatted.to_dict()

        # Check required fields
        for req in ["document_id", "document_version", "chunk_id", "section_path", "page_start", "page_end", "chunk_index", "parent_section_id", "token_count", "quality_flags", "source_text", "embedding_text"]:
            self.assertIn(req, d)

        # Check heading prefix format
        self.assertTrue(chunk.embedding_text.startswith("Document: The Ten Step Social Media Strategy Blueprint"))
        self.assertIn("Section: Step One — The Destination", chunk.embedding_text)
        self.assertIn("Subsection: Four Tips for Goal Setting", chunk.embedding_text)

        # Check source text does not have prefix
        self.assertFalse(chunk.source_text.startswith("Document:"))


class TestInstruction6_ValidationAndManifest(unittest.TestCase):
    """Test Instruction 6: Add validation before embedding."""

    def test_validation_flags_and_manifest(self):
        validator = ChunkValidator()
        extracted_doc = ExtractedDocument(
            document_id="blueprint_doc", source_file="doc.pdf", file_type="pdf",
            page_count=10,
            blocks=[
                ExtractedBlock(block_id="b1", page_num=1, bbox=(0,0,10,10), text="Step One: Destination"),
                ExtractedBlock(block_id="b2", page_num=2, bbox=(0,0,10,10), text="0n the end`V\\^PSSILSLM[^P[O"),
            ],
            raw_text="", raw_extraction={}
        )

        # Chunk with garbled text
        garbled_chunk = StructuredChunk(
            chunk_id="c_garbled", document_id="blueprint_doc", document_version="1.0",
            section_path="Doc > Step One", parent_section_id=None, chunk_index=0,
            source_text="0n the end`V\\^PSSILSLM[^P[O",
            embedding_text="Doc > Step One\n\n0n the end`V\\^PSSILSLM[^P[O",
            token_count=15, page_start=2, page_end=2,
            quality_flags=[], source_block_ids=["b2"]
        )

        report = validator.validate_chunks([garbled_chunk], extracted_doc)
        self.assertFalse(report.is_valid)
        self.assertIn("garbled_flagged", garbled_chunk.quality_flags)
        self.assertEqual(report.flagged_chunks_count, 1)
        self.assertEqual(report.manifest.total_blocks, 2)

    def test_document_store_deduplication(self):
        store = DocumentStoreDeduplicator()
        c1 = StructuredChunk(chunk_id="c1", document_id="doc_A", document_version="1.0", section_path="A", parent_section_id=None, chunk_index=0, source_text="Text 1", embedding_text="A\n\nText 1", token_count=10, page_start=1, page_end=1)
        c2 = StructuredChunk(chunk_id="c2", document_id="doc_A", document_version="2.0", section_path="A", parent_section_id=None, chunk_index=0, source_text="Text 2", embedding_text="A\n\nText 2", token_count=10, page_start=1, page_end=1)

        store.replace_document_chunks("doc_A", [c1])
        self.assertEqual(len(store.get_document_chunks("doc_A")), 1)

        # Reimport replaces chunks without duplicates
        prev, new_c = store.replace_document_chunks("doc_A", [c2])
        self.assertEqual(prev, 1)
        self.assertEqual(new_c, 1)
        self.assertEqual(store.get_document_chunks("doc_A")[0].source_text, "Text 2")


class TestInstruction7_RetrievalComparison(unittest.TestCase):
    """Test Instruction 7: Compare retrieval before and after."""

    def test_retrieval_benchmark_comparison(self):
        evaluator = RetrievalBenchmarkEvaluator()

        raw_chunks_baseline = [
            {
                "chunk_id": "chunk_001",
                "text": "Tent Social Marketing Strategy Series\nAbout Tent Social: Tent Social is a digital marketing agency.\n0n the end`V\\^PSSILSLM[^P[O h elp your brand grow.\nPage 1"
            },
            {
                "chunk_id": "chunk_002",
                "text": "Tent Social Marketing Strategy Series\nTable of Contents: Step One: The Destination ... 3, Step Two: The Audience ... 8.\nStep One — The Destination. Setting goals is essential for social media success."
            },
            {
                "chunk_id": "chunk_005",
                "text": "Tent Social Marketing Strategy Series\nYou must decide what you want to achieve over a 12-to-24 month period.\nMake It Medium To Long Term.\nPage 5"
            },
            {
                "chunk_id": "chunk_007",
                "text": "Tent Social Marketing Strategy Series\nFinancial vs non-financial metrics must both be measured.\nStep Two — The Audience. Now that you have set your destination, who are you speaking to?"
            }
        ]

        structured_chunks = [
            StructuredChunk(
                chunk_id="doc_step01_tips_c001",
                document_id="Social_Media_Strategy_Blueprint",
                document_version="1.0",
                section_path="The Ten Step Social Media Strategy Blueprint > Step One — The Destination > Four Tips for Goal Setting",
                parent_section_id="doc_step01",
                chunk_index=0,
                source_text="Four Tips for Goal Setting:\n1. Make It Medium To Long Term: Establish goals that span 12 to 24 months.\n2. Balance Financial and Non-Financial Goals: Align revenue targets with awareness.\n3. Be Realistic: Base milestones on historical baselines.\n4. Prioritize Key Metrics: Focus on conversion rate.",
                embedding_text="Document: The Ten Step Social Media Strategy Blueprint\nSection: Step One — The Destination\nSubsection: Four Tips for Goal Setting\n\nFour Tips for Goal Setting:\n1. Make It Medium To Long Term: Establish goals that span 12 to 24 months.\n2. Balance Financial and Non-Financial Goals: Align revenue targets with awareness.\n3. Be Realistic: Base milestones on historical baselines.\n4. Prioritize Key Metrics: Focus on conversion rate.",
                token_count=150, page_start=4, page_end=5, quality_flags=["clean"]
            ),
            StructuredChunk(
                chunk_id="doc_step02_audience_c001",
                document_id="Social_Media_Strategy_Blueprint",
                document_version="1.0",
                section_path="The Ten Step Social Media Strategy Blueprint > Step Two — The Audience > Audience Persona",
                parent_section_id="doc_step02",
                chunk_index=1,
                source_text="How to Build an Audience Persona:\nDefine target demographics (age, gender, location), core psychographics (interests, values), and active social media platforms.",
                embedding_text="Document: The Ten Step Social Media Strategy Blueprint\nSection: Step Two — The Audience\nSubsection: Audience Persona\n\nHow to Build an Audience Persona:\nDefine target demographics (age, gender, location), core psychographics (interests, values), and active social media platforms.",
                token_count=120, page_start=8, page_end=9, quality_flags=["clean"]
            )
        ]

        report = evaluator.evaluate_comparison(raw_chunks_baseline, structured_chunks)

        self.assertEqual(report.queries_evaluated, 2)
        # Structured system should achieve higher completeness & purity
        self.assertGreaterEqual(report.structured_summary["completeness"], report.baseline_summary["completeness"])
        self.assertGreater(report.structured_summary["noise_freedom"], report.baseline_summary["noise_freedom"])
        self.assertGreater(report.structured_summary["section_purity"], report.baseline_summary["section_purity"])
        self.assertGreater(len(report.improvement_highlights), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
