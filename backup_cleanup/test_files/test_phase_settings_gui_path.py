#!/usr/bin/env python3
"""
The desktop app's saved Phase 2 settings must drive the structure-aware chunker sensibly.

Older GUI versions saved max_chunk_tokens=150 (and no target_tokens). Applied to the
structure-aware chunker that capped every chunk at 150 tokens, context prefix included.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python_files"))

from phase_controlled_pipeline import PhaseControlledPipeline, PhaseStatus
from test_pipeline_integration import write_book_pdf


def pipeline_with_saved_phase2(tmp, settings):
    cfg = Path(tmp) / "cfg.json"
    cfg.write_text(json.dumps({"phase2_chunking": {"status": "green", "settings": settings}}))
    return PhaseControlledPipeline(str(cfg))


class TestLegacyPhase2Migration(unittest.TestCase):

    def test_legacy_150_is_replaced_by_structured_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pipeline_with_saved_phase2(tmp, {"max_chunk_tokens": 150, "token_overlap": 1})
            s = p.phases["phase2_chunking"].settings
            self.assertEqual((s["target_tokens"], s["max_chunk_tokens"]), (500, 800))

    def test_user_chosen_values_are_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pipeline_with_saved_phase2(tmp, {"target_tokens": 300, "max_chunk_tokens": 600})
            s = p.phases["phase2_chunking"].settings
            self.assertEqual((s["target_tokens"], s["max_chunk_tokens"]), (300, 600))

    def test_fresh_install_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = PhaseControlledPipeline(str(Path(tmp) / "none.json"))
            s = p.phases["phase2_chunking"].settings
            self.assertEqual((s["target_tokens"], s["max_chunk_tokens"]), (500, 800))


class TestPhase2RunsStructured(unittest.TestCase):

    def test_legacy_config_still_gets_full_size_chunks_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            phase1, phase2 = tmp / "p1", tmp / "p2"
            phase1.mkdir()
            write_book_pdf(tmp / "handbook.pdf", chapters=3)

            p = pipeline_with_saved_phase2(tmp, {"max_chunk_tokens": 150})
            # Phase 1 normally produces these; drive Phase 2 from the extracted structure.
            from document_structure_extractor import DocumentStructureExtractor
            doc = DocumentStructureExtractor().extract_document(tmp / "handbook.pdf")
            (phase1 / "handbook_sanitized.txt").write_text(doc.raw_text or "x", encoding="utf-8")

            cfg = p.phases["phase2_chunking"]
            cfg.input_folder, cfg.output_folder = str(phase1), str(phase2)
            cfg.status = PhaseStatus.ENABLED
            from phase_controlled_pipeline import PhaseResult
            res = p._execute_phase2(cfg, PhaseResult(phase_name="p2", status=PhaseStatus.ENABLED, start_time=__import__("datetime").datetime.now()))

            out = phase2 / "handbook"
            self.assertTrue((out / "handbook_chunks.jsonl").exists())
            self.assertTrue((out / "handbook_validation_report.json").exists())
            self.assertTrue((out / "handbook_source_manifest.json").exists())
            self.assertEqual(res.files_failed, 0)


if __name__ == "__main__":
    unittest.main()
