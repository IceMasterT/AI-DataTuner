#!/usr/bin/env python3
"""Operational health checks for the AI data pipeline."""

import argparse
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from phase_controlled_pipeline import PhaseControlledPipeline, PhaseResult, PhaseStatus


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _ok(label: str, detail: str = ""):
    print(f"[OK] {label}{': ' + detail if detail else ''}")


def _warn(label: str, detail: str = ""):
    print(f"[WARN] {label}{': ' + detail if detail else ''}")


def _fail(label: str, detail: str = ""):
    print(f"[FAIL] {label}{': ' + detail if detail else ''}")


def check_environment(init_folders: bool = False, strict: bool = False) -> bool:
    passed = True
    _ok("Python", sys.version.split()[0])

    provider = (
        (os.getenv("OPENAI_PROVIDER") or os.getenv("PROVIDER") or "openai")
        .strip()
        .lower()
    )
    key_name = None
    if provider == "openrouter":
        key_name = "OPENROUTER_API_KEY"
    elif provider == "openai":
        key_name = "OPENAI_API_KEY"

    if key_name is None:
        _ok("Provider auth", f"{provider} selected (no API key required)")
    else:
        key = os.getenv(key_name)
        placeholder_like = bool(key) and (
            key.strip().startswith("<")
            or "YOUR_" in key
            or "SET_" in key
            or "PLACEHOLDER" in key.upper()
        )

        if key and not placeholder_like:
            _ok(f"{key_name}", f"set (provider={provider})")
        else:
            if strict:
                _fail(
                    f"{key_name}",
                    f"missing/placeholder (provider={provider}; strict mode requires real credentials)",
                )
                passed = False
            else:
                _warn(
                    f"{key_name}",
                    f"missing/placeholder (provider={provider}; enhanced formatter will fallback)",
                )

    for folder in ["input", "Phase 1", "Phase 2", "Phase 3", "Phase 4", "config"]:
        p = PROJECT_ROOT / folder
        if p.exists():
            _ok("Folder", str(p))
        else:
            if init_folders:
                p.mkdir(parents=True, exist_ok=True)
                _ok("Folder created", str(p))
            else:
                _warn("Folder missing", str(p))

    dependencies = {
        "openai": "AI enhancement and strict formatting",
        "yaml": "YAML configuration support",
        "nltk": "advanced text chunking",
        "PyPDF2": "PDF extraction fallback",
    }
    for module_name, purpose in dependencies.items():
        try:
            __import__(module_name)
            _ok("Dependency", f"{module_name} ({purpose})")
        except Exception:
            if strict:
                _fail("Dependency missing", f"{module_name} ({purpose})")
                passed = False
            else:
                _warn("Dependency missing", f"{module_name} ({purpose})")

    return passed


def check_pipeline_config() -> bool:
    passed = True
    try:
        pipeline = PhaseControlledPipeline()
        _ok("Pipeline config path", str(pipeline.config_file))

        enabled = pipeline.get_enabled_phases()
        if enabled:
            _ok("Enabled phases", ", ".join(enabled))
        else:
            _fail("Enabled phases", "none enabled")
            passed = False

        p1 = pipeline.phases["phase1_sanitization"].settings
        p3 = pipeline.phases["phase3_personality"].settings
        required_p1 = [
            "max_clean_file_size_mb",
            "size_cap_unit",
            "size_cap_strategy",
            "on_cap_exceeded",
            "recursive_input_scan",
            "min_clean_chars",
            "drop_empty_outputs",
            "finetune_safe_cleaning",
            "unicode_normalization_form",
            "max_consecutive_blank_lines",
        ]
        required_p3 = ["training_target", "strict_role_validation"]

        missing_p1 = [k for k in required_p1 if k not in p1]
        missing_p3 = [k for k in required_p3 if k not in p3]

        if missing_p1:
            _fail("Phase 1 settings", f"missing {missing_p1}")
            passed = False
        else:
            _ok("Phase 1 settings", "size cap options present")

        if missing_p3:
            _fail("Phase 3 settings", f"missing {missing_p3}")
            passed = False
        else:
            _ok("Phase 3 settings", "training protocol options present")

        claude_protocol = pipeline._resolve_training_protocol(
            {"training_target": "claude"}
        )
        claude_text = pipeline._fallback_formatting(
            "Example answer", "instruct", "professional"
        )
        if pipeline._validate_training_output(claude_text, claude_protocol, True):
            _ok("Claude protocol", "fallback formatting passes strict markers")
        else:
            _fail("Claude protocol", "fallback formatting missing strict markers")
            passed = False

        required_phase_chain = [
            "phase1_sanitization",
            "phase2_chunking",
            "phase3_personality",
            "phase4_quality",
        ]
        missing_enabled = [p for p in required_phase_chain if p not in enabled]
        if missing_enabled:
            _warn("Phase chain", f"Not fully enabled: {missing_enabled}")
        else:
            _ok("Phase chain", "all phases enabled")

    except Exception as e:
        _fail("Pipeline config", str(e))
        passed = False

    return passed


def run_smoke_flow() -> bool:
    passed = True
    root = Path(tempfile.mkdtemp(prefix="pipeline-health-"))
    try:
        inp = root / "input"
        p1 = root / "Phase 1"
        p2 = root / "Phase 2"
        p3 = root / "Phase 3"
        inp.mkdir(parents=True)

        payload = "Alpha sentence. Beta sentence. Gamma sentence. " * 60
        (inp / "health_sample.txt").write_text(payload, encoding="utf-8")

        pipeline = PhaseControlledPipeline()

        c1 = pipeline.phases["phase1_sanitization"]
        c1.input_folder = str(inp)
        c1.output_folder = str(p1)
        c1.settings.update(
            {
                "max_clean_file_size_mb": 0.002,
                "size_cap_unit": "mb",
                "size_cap_strategy": "split",
                "preserve_sentence_boundaries": True,
                "on_cap_exceeded": "warn",
                "compression_mode": "none",
            }
        )
        r1 = pipeline._execute_phase1(
            c1, PhaseResult("phase1_sanitization", PhaseStatus.RUNNING, datetime.now())
        )

        c2 = pipeline.phases["phase2_chunking"]
        c2.input_folder = str(p1)
        c2.output_folder = str(p2)
        r2 = pipeline._execute_phase2(
            c2, PhaseResult("phase2_chunking", PhaseStatus.RUNNING, datetime.now())
        )

        c3 = pipeline.phases["phase3_personality"]
        c3.input_folder = str(p2)
        c3.output_folder = str(p3)
        c3.settings.update(
            {
                "training_target": "alpaca",
                "strict_role_validation": True,
                "output_format": "alpaca",
            }
        )
        r3 = pipeline._execute_phase3(
            c3, PhaseResult("phase3_personality", PhaseStatus.RUNNING, datetime.now())
        )

        if r1.files_processed < 1 or r1.files_failed > 0:
            _fail(
                "Smoke Phase 1",
                f"processed={r1.files_processed}, failed={r1.files_failed}",
            )
            passed = False
        else:
            _ok("Smoke Phase 1", f"outputs={len(r1.output_files)}")

        if r2.files_processed < 1 or r2.files_failed > 0:
            _fail(
                "Smoke Phase 2",
                f"processed={r2.files_processed}, failed={r2.files_failed}",
            )
            passed = False
        else:
            _ok("Smoke Phase 2", f"chunks={len(r2.output_files)}")

        if r3.files_processed < 1 or r3.files_failed > 0:
            _fail(
                "Smoke Phase 3",
                f"processed={r3.files_processed}, failed={r3.files_failed}",
            )
            passed = False
        else:
            _ok("Smoke Phase 3", f"outputs={len(r3.output_files)}")

    except Exception as e:
        _fail("Smoke flow", str(e))
        passed = False
    finally:
        shutil.rmtree(root, ignore_errors=True)

    return passed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run pipeline operational health checks"
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run synthetic phase 1-3 smoke flow",
    )
    parser.add_argument(
        "--init-folders",
        action="store_true",
        help="create missing root pipeline folders before checks",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail on missing credentials/dependencies",
    )
    args = parser.parse_args()

    print("AI Data Pipeline Health Check")
    print("=" * 32)

    checks = [
        check_environment(init_folders=args.init_folders, strict=args.strict),
        check_pipeline_config(),
    ]
    if args.smoke:
        checks.append(run_smoke_flow())

    ok = all(checks)
    print("-" * 32)
    if ok:
        print("HEALTH CHECK: PASS")
        return 0
    print("HEALTH CHECK: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
