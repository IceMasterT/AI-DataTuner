#!/usr/bin/env python3
"""
Tests for pipeline wiring and generalised validation:
- unit-coverage validation for any numbered document (not just "Ten Step")
- retrieval benchmark on a real file (`evaluate-retrieval --file`)
- structure-aware chunking inside the workflow orchestrator (`start` / `process`)
"""

import argparse
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python_files"))

import pymupdf

from chunk_validator import ChunkValidator
from document_structure_extractor import ExtractedBlock, ExtractedDocument
from structured_chunker import StructuredChunk
from retrieval_evaluator import RetrievalBenchmarkEvaluator


def make_doc(doc_id, heading_texts):
    blocks = [
        ExtractedBlock(block_id=f"h{i}", page_num=i + 1, bbox=(0, 0, 10, 10),
                       text=t, is_heading=True, heading_level=1)
        for i, t in enumerate(heading_texts)
    ]
    return ExtractedDocument(document_id=doc_id, source_file="x.pdf", file_type="pdf",
                             page_count=len(blocks), blocks=blocks, raw_text="", raw_extraction={})


def make_chunk(idx, title, section, body="Some genuine body text for this section."):
    return StructuredChunk(
        chunk_id=f"c{idx}", document_id="d", document_version="1.0",
        section_path=f"{title} > {section}", parent_section_id=None, chunk_index=idx,
        source_text=body, embedding_text=f"Document: {title}\nSection: {section}\n\n{body}",
        token_count=10, page_start=idx + 1, page_end=idx + 1, quality_flags=[], source_block_ids=[f"h{idx}"],
    )


def write_book_pdf(path, chapters=6):
    topics = [
        ("Goals", "goal milestone objective timeline quarterly target alignment"),
        ("Audience", "audience persona segment demographic psychographic interview survey"),
        ("Channels", "channel platform algorithm posting cadence engagement hashtag"),
        ("Content", "content calendar storytelling headline visual caption formats"),
        ("Metrics", "metric dashboard conversion attribution benchmark funnel retention"),
        ("Budget", "budget allocation forecast spend invoice contractor overhead"),
    ][:chapters]
    doc = pymupdf.open()
    for i, (title, words) in enumerate(topics, 1):
        page = doc.new_page()
        page.insert_text((72, 40), "Acme Growth Handbook Series", fontsize=9)
        page.insert_text((72, 100), f"Chapter {i}: {title}", fontsize=20)
        body = f"This chapter explains {title.lower()} in depth. " + " ".join(
            f"Teams should review {w} regularly and record what they learn about {w}." for w in words.split())
        page.insert_textbox(pymupdf.Rect(72, 130, 520, 500), body, fontsize=11)
        page.insert_text((280, 800), f"Page {i}", fontsize=9)
    doc.save(str(path))
    doc.close()


class TestGeneralisedCoverageValidation(unittest.TestCase):

    def setUp(self):
        self.v = ChunkValidator()

    def coverage_issues(self, report):
        return [i for i in report.issues if i.issue_type == "incomplete_coverage"]

    def test_missing_chapter_from_source_headings_is_an_error(self):
        doc = make_doc("field_guide", ["Chapter 1: Start", "Chapter 2: Middle", "Chapter 3: End"])
        chunks = [make_chunk(0, "Field Guide", "Chapter 1: Start"), make_chunk(1, "Field Guide", "Chapter 2: Middle")]
        report = self.v.validate_chunks(chunks, doc)
        self.assertFalse(report.is_valid)
        self.assertEqual(report.missing_expected_steps, ["Chapter 3"])
        self.assertEqual(len(self.coverage_issues(report)), 1)

    def test_complete_document_has_no_coverage_issue(self):
        doc = make_doc("field_guide", ["Chapter 1: Start", "Chapter 2: Middle"])
        chunks = [make_chunk(0, "Field Guide", "Chapter 1: Start"), make_chunk(1, "Field Guide", "Chapter 2: Middle")]
        report = self.v.validate_chunks(chunks, doc)
        self.assertEqual(self.coverage_issues(report), [])
        self.assertEqual(report.missing_expected_steps, [])
        self.assertEqual(report.steps_detected, ["Chapter 1", "Chapter 2"])

    def test_document_without_numbered_structure_is_not_checked(self):
        doc = make_doc("meeting_notes", ["Overview", "Decisions"])
        chunks = [make_chunk(0, "Meeting Notes", "Overview")]
        report = self.v.validate_chunks(chunks, doc)
        self.assertEqual(self.coverage_issues(report), [])
        self.assertEqual(report.steps_detected, [])

    def test_title_declared_count_expects_every_unit(self):
        # Declared by title: "Seven Step" -> Step 1..7 all expected, even with no source headings
        doc = make_doc("seven-step-plan", ["Introduction"])
        chunks = [make_chunk(i, "Seven Step Plan", f"Step {i + 1}") for i in range(5)]
        report = self.v.validate_chunks(chunks, doc)
        self.assertEqual(report.missing_expected_steps, ["Step 6", "Step 7"])
        self.assertFalse(report.is_valid)

    def test_number_words_and_digits_are_equivalent(self):
        doc = make_doc("blueprint", ["Step One — Goals", "Step Two — Audience"])
        chunks = [make_chunk(0, "Blueprint", "Step 1 — Goals"), make_chunk(1, "Blueprint", "Step 2 — Audience")]
        report = self.v.validate_chunks(chunks, doc)
        self.assertEqual(report.missing_expected_steps, [])

    def test_gap_in_source_numbering_is_a_warning(self):
        doc = make_doc("guide", ["Part 1: A", "Part 3: C"])
        chunks = [make_chunk(0, "Guide", "Part 1: A"), make_chunk(1, "Guide", "Part 3: C")]
        report = self.v.validate_chunks(chunks, doc)
        gaps = [i for i in report.issues if i.issue_type == "numbering_gap"]
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].severity, "warning")
        self.assertTrue(report.is_valid)  # a warning alone does not invalidate


class TestRealFileBenchmark(unittest.TestCase):

    def test_build_cases_and_custom_furniture(self):
        from section_hierarchy_builder import SectionHierarchyBuilder
        from furniture_cleaner import FurnitureCleaner
        from document_structure_extractor import DocumentStructureExtractor

        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "book.pdf"
            write_book_pdf(pdf)
            doc = DocumentStructureExtractor(enable_ocr=False).extract_document(pdf)
            cleaned = FurnitureCleaner().clean_document(doc)
            hierarchy = SectionHierarchyBuilder().build_hierarchy(cleaned.cleaned_blocks, doc.document_id)
            cases = RetrievalBenchmarkEvaluator.build_cases_from_hierarchy(hierarchy)
            self.assertEqual(len(cases), 6)
            for c in cases:
                self.assertGreaterEqual(len(c["expected_elements"]), 2)
                self.assertIn("Chapter", c["query"])

    def test_naive_chunker_windows_text(self):
        chunks = RetrievalBenchmarkEvaluator.naive_chunk_text("x" * 2500, size=1000, overlap=100)
        self.assertEqual(len(chunks), 3)
        self.assertNotIn("Document:", chunks[0]["embedding_text"])

    def test_highlights_report_regressions_honestly(self):
        from structured_chunker import StructuredChunk as SC
        good_baseline = [{"chunk_id": "b", "text": "alpha beta gamma delta", "embedding_text": "alpha beta gamma delta"}]
        worse = [SC(chunk_id="s", document_id="d", document_version="1", section_path="", parent_section_id=None,
                    chunk_index=0, source_text="unrelated words entirely", embedding_text="unrelated words entirely",
                    token_count=3, page_start=1, page_end=1)]
        cases = [{"query": "alpha beta gamma delta", "expected_elements": ["alpha", "beta", "gamma", "delta"],
                  "target_section": "x"}]
        report = RetrievalBenchmarkEvaluator().evaluate_comparison(good_baseline, worse, cases=cases, furniture_samples=[])
        completeness_line = report.improvement_highlights[0]
        self.assertIn("regressed", completeness_line)
        self.assertNotIn("improved", completeness_line)

    def test_cli_evaluate_retrieval_uses_the_given_file(self):
        import pipeline_cli
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "book.pdf"
            write_book_pdf(pdf)
            out = Path(tmp) / "report.json"
            args = argparse.Namespace(file=str(pdf), output_report=str(out))
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = pipeline_cli.handle_evaluate_retrieval_command(args)
            self.assertEqual(rc, 0, buf.getvalue())
            self.assertIn("book.pdf", buf.getvalue())
            report = json.loads(out.read_text())
            self.assertEqual(report["queries_evaluated"], 6)
            # Noise must be judged against this document's own furniture, not the synthetic sample
            self.assertEqual(report["structured_summary"]["noise_freedom"], "100.0%")
            self.assertEqual(report["baseline_summary"]["noise_freedom"], "0.0%")

    def test_cli_evaluate_retrieval_missing_file_fails(self):
        import pipeline_cli
        args = argparse.Namespace(file="/nonexistent/nope.pdf", output_report="unused.json")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(pipeline_cli.handle_evaluate_retrieval_command(args), 1)


class TestOrchestratorStructuredChunking(unittest.TestCase):

    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def make_orchestrator(self, **overrides):
        from env_config import EnvironmentConfig
        from workflow_orchestrator import WorkflowOrchestrator
        cfg = EnvironmentConfig()
        cfg.enable_security_filtering = False
        cfg.enable_ai_classification = False
        cfg.auto_move_files = False
        for k, v in overrides.items():
            setattr(cfg, k, v)
        return WorkflowOrchestrator(cfg)

    def test_pdf_gets_structure_aware_chunks(self):
        orch = self.make_orchestrator()
        self.assertIn("structured_chunking", [s.name for s in orch.stages if s.enabled])
        pdf = Path(self._tmp.name) / "book.pdf"
        write_book_pdf(pdf)

        result = orch.process_file_through_workflow(pdf)

        self.assertTrue(result.success, result.error_message)
        self.assertIn("structured_chunking", result.stages_completed)
        jsonl = Path("output") / "book" / "book_chunks.jsonl"
        self.assertTrue(jsonl.exists())
        rows = [json.loads(line) for line in jsonl.read_text().splitlines() if line.strip()]
        self.assertEqual(len(rows), 6)
        self.assertTrue(all("Section:" in r["embedding_text"] for r in rows))
        self.assertTrue((Path("output") / "book" / "book_validation_report.json").exists())
        self.assertTrue((Path("output") / "book" / "book_source_manifest.json").exists())
        # The text chain still ran and its output is still the primary result
        self.assertIn("file_extraction", result.stages_completed)

    def test_unsupported_type_skips_stage_without_failing(self):
        orch = self.make_orchestrator()
        csv = Path(self._tmp.name) / "table.csv"
        csv.write_text("name,notes\nalpha,first row with enough text to extract\nbeta,second row with more text\n")
        result = orch.process_file_through_workflow(csv)
        self.assertTrue(result.success, result.error_message)
        self.assertNotIn("structured_chunking", result.stages_completed)
        self.assertNotIn("structured_chunking", result.stages_failed)
        self.assertFalse((Path("output") / "table").exists())

    def test_can_be_disabled(self):
        orch = self.make_orchestrator(enable_structured_chunking=False)
        pdf = Path(self._tmp.name) / "book.pdf"
        write_book_pdf(pdf, chapters=2)
        result = orch.process_file_through_workflow(pdf)
        self.assertTrue(result.success, result.error_message)
        self.assertNotIn("structured_chunking", result.stages_completed)
        self.assertFalse((Path("output") / "book").exists())


if __name__ == "__main__":
    unittest.main()
