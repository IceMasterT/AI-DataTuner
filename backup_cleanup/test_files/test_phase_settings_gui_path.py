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


class TestPhase3Formats(unittest.TestCase):
    """Every format offered in the Processing tab must be written as itself, not as qwen."""

    MARKERS = {
        "qwen": "<|user|>", "alpaca": "### Instruction:", "chatml": "<|im_start|>",
        "sharegpt": '"from"', "llama2": "[INST]", "gpt_jsonl": '"messages"',
        "zephyr": "- role: user", "instruct": "Question:", "claude": "Human:",
        "minimalist": "User:",
    }

    def test_all_ten_formats_render_distinctly(self):
        import datetime
        from phase_controlled_pipeline import PhaseResult
        for fmt, marker in self.MARKERS.items():
            with self.subTest(fmt=fmt), tempfile.TemporaryDirectory() as t:
                t = Path(t)
                (t / "in").mkdir()
                (t / "in" / "a.txt").write_text("Body text.", encoding="utf-8")
                p = PhaseControlledPipeline(str(t / "c.json"))
                c = p.phases["phase3_personality"]
                c.input_folder, c.output_folder = str(t / "in"), str(t / "out")
                c.settings.update(training_target=fmt, output_format=fmt, emit_combined_jsonl=False)
                r = p._execute_phase3(c, PhaseResult(phase_name="p3", status=PhaseStatus.ENABLED,
                                                     start_time=datetime.datetime.now()))
                self.assertEqual(r.files_failed, 0, r.errors)
                out = next((t / "out").rglob("a.*")).read_text(encoding="utf-8")
                self.assertIn(marker, out)
                if fmt != "qwen":
                    self.assertNotIn("<|user|>", out)


class TestPillarsReporting(unittest.TestCase):

    def test_implemented_count_is_not_overstated(self):
        from ten_pillars_integration import TenPillarsIntegration
        self.assertEqual(len(TenPillarsIntegration.IMPLEMENTED_PILLARS), 7)


class TestLaunchGate(unittest.TestCase):
    """run_pipeline.sh refuses to open the app when the health check fails."""

    def test_pipeline_config_health_check_passes(self):
        import operational_health_check as ohc
        self.assertTrue(ohc.check_pipeline_config())


class TestProgressReporting(unittest.TestCase):
    """The progress bar must move during a run, not jump from 0 to 100."""

    def test_progress_advances_monotonically_and_reaches_phase_boundaries(self):
        import threading, time
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "in").mkdir()
            for i in range(6):
                write_book_pdf(tmp / "in" / f"book{i}.pdf", chapters=2)
            p = PhaseControlledPipeline(str(tmp / "cfg.json"))
            folders = [tmp / "in", tmp / "p1", tmp / "p2", tmp / "p3", tmp / "p4"]
            for name, (src, dst) in zip(
                ("phase1_sanitization", "phase2_chunking", "phase3_personality", "phase4_quality"),
                zip(folders, folders[1:]),
            ):
                p.phases[name].input_folder, p.phases[name].output_folder = str(src), str(dst)
                p.phases[name].status = PhaseStatus.ENABLED if name in (
                    "phase1_sanitization", "phase2_chunking") else PhaseStatus.DISABLED
            self.assertFalse(p.get_progress()["running"])

            samples = []
            t = threading.Thread(target=p.start_pipeline)
            t.start()
            while t.is_alive():
                samples.append(p.get_progress())
                time.sleep(0.005)
            t.join()

            pcts = [s["percent"] for s in samples if s["running"]]
            self.assertTrue(pcts, "no progress sampled while running")
            self.assertEqual(pcts, sorted(pcts), "progress went backwards")
            self.assertTrue(any(0 < v < 100 for v in pcts), f"never intermediate: {pcts[:5]}")
            self.assertTrue(all(s["phase_count"] == 2 for s in samples if s["running"]))
            self.assertFalse(p.get_progress()["running"])
