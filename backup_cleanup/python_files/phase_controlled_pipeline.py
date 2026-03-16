#!/usr/bin/env python3
"""
Phase-Controlled LLM Data Preparation Pipeline
Multi-phase system with red light/green light phase control for precise data preparation.
"""

import json
import time
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import logging


class PhaseStatus(Enum):
    """Phase execution status."""

    DISABLED = "red"  # Red light - skip phase
    ENABLED = "green"  # Green light - execute phase
    RUNNING = "yellow"  # Currently executing
    COMPLETE = "blue"  # Completed successfully
    ERROR = "orange"  # Error occurred


@dataclass
class PhaseConfig:
    """Configuration for a pipeline phase."""

    name: str
    description: str
    status: PhaseStatus = PhaseStatus.ENABLED
    input_folder: str = ""
    output_folder: str = ""
    settings: Dict[str, Any] = None

    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


@dataclass
class PhaseResult:
    """Result of phase execution."""

    phase_name: str
    status: PhaseStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    files_processed: int = 0
    files_failed: int = 0
    output_files: List[str] = None
    errors: List[str] = None
    metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.output_files is None:
            self.output_files = []
        if self.errors is None:
            self.errors = []
        if self.metrics is None:
            self.metrics = {}


class PhaseControlledPipeline:
    """Main pipeline with phase control system."""

    def __init__(self, config_file: str = "pipeline_phases.json"):
        self.logger = logging.getLogger(__name__)
        self.config_file = self._resolve_config_path(config_file)

        # Initialize phases
        self.phases = self._initialize_phases()
        self.results: Dict[str, PhaseResult] = {}

        # Load configuration if exists
        self.load_configuration()

        # Pipeline state
        self.is_running = False
        self.current_phase = None
        self.abort_requested = False
        self.pause_requested = False

    def _resolve_config_path(self, config_file: str) -> Path:
        """Resolve config path with sensible fallbacks across launch directories."""
        given = Path(config_file)
        if given.is_absolute():
            return given

        project_root = Path(__file__).resolve().parents[2]
        candidates = [
            Path.cwd() / given,
            Path.cwd() / "config" / given.name,
            project_root / given,
            project_root / "config" / given.name,
            project_root / "backup_cleanup" / "config_files" / given.name,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return project_root / "config" / given.name

    def _initialize_phases(self) -> Dict[str, PhaseConfig]:
        """Initialize all pipeline phases."""
        project_root = self.config_file.parent.parent
        input_dir = str(project_root / "input")
        phase1_dir = str(project_root / "Phase 1")
        phase2_dir = str(project_root / "Phase 2")
        phase3_dir = str(project_root / "Phase 3")
        phase4_dir = str(project_root / "Phase 4")

        return {
            "phase1_sanitization": PhaseConfig(
                name="Input Parsing & Sanitization",
                description="Parse files and sanitize data for safe processing",
                input_folder=input_dir,
                output_folder=phase1_dir,
                settings={
                    "supported_formats": ["pdf", "csv", "json", "jsonl", "txt", "md"],
                    "security_level": "balanced",
                    "unicode_normalization": True,
                    "remove_markup": True,
                    "filter_code": True,
                    "remove_tables": False,
                    "max_clean_file_size_mb": 0,
                    "size_cap_strategy": "split",
                    "preserve_sentence_boundaries": True,
                    "compression_mode": "none",
                    "on_cap_exceeded": "warn",
                    "recursive_input_scan": False,
                    "min_clean_chars": 1,
                    "drop_empty_outputs": True,
                    "finetune_safe_cleaning": True,
                    "unicode_normalization_form": "NFKC",
                    "max_consecutive_blank_lines": 2,
                },
            ),
            "phase2_chunking": PhaseConfig(
                name="Chunking & Fact Extraction",
                description="Divide text into manageable, coherent chunks",
                input_folder=phase1_dir,
                output_folder=phase2_dir,
                settings={
                    "chunk_size": "1-2_sentences",
                    "token_overlap": 1,
                    "max_chunk_tokens": 150,
                    "preserve_context": True,
                    "fact_extraction": True,
                    "create_subfolders": True,
                },
            ),
            "phase3_personality": PhaseConfig(
                name="Personality Prompting & Formatting",
                description="Transform chunks with personality-driven prompting",
                input_folder=phase2_dir,
                output_folder=phase3_dir,
                settings={
                    "personality_template": "professional",
                    "personality_strength": 0.7,
                    "maintain_factual_accuracy": True,
                    "format_validation": True,
                    "output_format": "qwen",
                    "batch_size": 10,
                    "training_target": "qwen",
                    "strict_role_validation": True,
                    "emit_combined_jsonl": True,
                    "combined_jsonl_filename": "chatgpt_training.jsonl",
                },
            ),
            "phase4_quality": PhaseConfig(
                name="Quality Scoring & Assessment",
                description="LLM-powered quality evaluation and scoring",
                input_folder=phase3_dir,
                output_folder=phase4_dir,
                settings={
                    "scoring_model": "gpt-4o",
                    "quality_metrics": ["accuracy", "fluency", "personality_depth"],
                    "score_scale": 100,
                    "sample_percentage": 10,
                    "generate_report": True,
                    "auto_download": False,
                },
            ),
        }

    def get_phase_status(self, phase_name: str) -> PhaseStatus:
        """Get current status of a phase."""
        return self.phases.get(phase_name, PhaseConfig("", "")).status

    def set_phase_status(self, phase_name: str, status: PhaseStatus) -> bool:
        """Set phase status (red/green light control)."""
        if phase_name in self.phases:
            self.phases[phase_name].status = status
            self.save_configuration()
            self.logger.info(f"Phase {phase_name} status set to {status.value}")
            return True
        return False

    def toggle_phase(self, phase_name: str) -> PhaseStatus:
        """Toggle phase between enabled/disabled."""
        if phase_name in self.phases:
            current = self.phases[phase_name].status
            if current == PhaseStatus.ENABLED:
                new_status = PhaseStatus.DISABLED
            else:
                new_status = PhaseStatus.ENABLED

            self.set_phase_status(phase_name, new_status)
            return new_status
        return PhaseStatus.DISABLED

    def get_enabled_phases(self) -> List[str]:
        """Get list of enabled (green light) phases."""
        return [
            name
            for name, config in self.phases.items()
            if config.status == PhaseStatus.ENABLED
        ]

    def update_phase_settings(self, phase_name: str, settings: Dict[str, Any]) -> bool:
        """Update settings for a specific phase."""
        if phase_name in self.phases:
            self.phases[phase_name].settings.update(settings)
            self.save_configuration()
            return True
        return False

    def start_pipeline(self) -> Dict[str, PhaseResult]:
        """Start pipeline execution (only green-lit phases)."""
        if self.is_running:
            raise RuntimeError("Pipeline is already running")

        self.is_running = True
        self.abort_requested = False
        self.pause_requested = False
        self.results = {}

        enabled_phases = self.get_enabled_phases()
        self.logger.info(f"Starting pipeline with {len(enabled_phases)} enabled phases")

        # Validate folder structure and data flow
        self._validate_pipeline_setup(enabled_phases)

        try:
            for phase_name in enabled_phases:
                if self.abort_requested:
                    self.logger.info("Pipeline aborted by user")
                    break

                # Handle pause
                while self.pause_requested and not self.abort_requested:
                    time.sleep(0.1)

                if self.abort_requested:
                    break

                # Validate input data exists for this phase
                if not self._validate_phase_input(phase_name):
                    self.logger.error(f"Phase {phase_name} input validation failed")
                    break

                # Execute phase
                self.current_phase = phase_name
                self.phases[phase_name].status = PhaseStatus.RUNNING

                result = self._execute_phase(phase_name)
                self.results[phase_name] = result

                if result.status == PhaseStatus.ERROR:
                    self.logger.error(f"Phase {phase_name} failed, stopping pipeline")
                    break

                # Validate output was created
                if not self._validate_phase_output(phase_name, result):
                    self.logger.error(f"Phase {phase_name} output validation failed")
                    break

                self.phases[phase_name].status = PhaseStatus.COMPLETE
                self.logger.info(
                    f"Phase {phase_name} completed successfully - data transferred to {self.phases[phase_name].output_folder}"
                )

        finally:
            self.is_running = False
            self.current_phase = None

        return self.results

    def _validate_pipeline_setup(self, enabled_phases: List[str]):
        """Validate pipeline setup and folder structure."""
        # Create all necessary folders
        for phase_name in enabled_phases:
            phase_config = self.phases[phase_name]

            # Create output folder
            output_path = Path(phase_config.output_folder)
            output_path.mkdir(exist_ok=True)
            self.logger.info(f"Ensured folder exists: {output_path}")

            # Validate input folder exists (except for first phase)
            if phase_name != "phase1_sanitization":
                input_path = Path(phase_config.input_folder)
                if not input_path.exists():
                    self.logger.warning(f"Input folder does not exist: {input_path}")

    def _validate_phase_input(self, phase_name: str) -> bool:
        """Validate that input data exists for a phase."""
        phase_config = self.phases[phase_name]
        input_path = Path(phase_config.input_folder)

        # For Phase 1, check input folder
        if phase_name == "phase1_sanitization":
            if not input_path.exists():
                self.logger.error(f"Input folder does not exist: {input_path}")
                return False

            # Check for files to process
            supported_extensions = [".pdf", ".csv", ".json", ".jsonl", ".txt", ".md"]
            input_files = []
            for ext in supported_extensions:
                input_files.extend(input_path.glob(f"*{ext}"))

            if not input_files:
                self.logger.error(
                    f"No supported files found in input folder: {input_path}"
                )
                return False

            self.logger.info(
                f"Phase 1 input validation: Found {len(input_files)} files to process"
            )
            return True

        # For other phases, check previous phase output
        if not input_path.exists():
            self.logger.error(
                f"Input folder does not exist for {phase_name}: {input_path}"
            )
            return False

        # Check for files from previous phase
        input_files = list(input_path.rglob("*"))
        input_files = [f for f in input_files if f.is_file()]

        if not input_files:
            self.logger.error(f"No input files found for {phase_name} in: {input_path}")
            return False

        self.logger.info(
            f"{phase_name} input validation: Found {len(input_files)} files from previous phase"
        )
        return True

    def _validate_phase_output(self, phase_name: str, result: PhaseResult) -> bool:
        """Validate that phase produced expected output."""
        phase_config = self.phases[phase_name]
        output_path = Path(phase_config.output_folder)

        if not output_path.exists():
            self.logger.error(
                f"Output folder was not created for {phase_name}: {output_path}"
            )
            return False

        # Check that files were created
        if result.files_processed == 0:
            self.logger.error(f"No files were processed in {phase_name}")
            return False

        # Check that output files exist
        output_files = list(output_path.rglob("*"))
        output_files = [f for f in output_files if f.is_file()]

        if not output_files:
            self.logger.error(f"No output files created in {phase_name}: {output_path}")
            return False

        self.logger.info(
            f"{phase_name} output validation: Created {len(output_files)} files in {output_path}"
        )
        return True

    def _execute_phase(self, phase_name: str) -> PhaseResult:
        """Execute a specific phase."""
        phase_config = self.phases[phase_name]
        result = PhaseResult(
            phase_name=phase_name, status=PhaseStatus.RUNNING, start_time=datetime.now()
        )

        try:
            if phase_name == "phase1_sanitization":
                result = self._execute_phase1(phase_config, result)
            elif phase_name == "phase2_chunking":
                result = self._execute_phase2(phase_config, result)
            elif phase_name == "phase3_personality":
                result = self._execute_phase3(phase_config, result)
            elif phase_name == "phase4_quality":
                result = self._execute_phase4(phase_config, result)
            else:
                raise ValueError(f"Unknown phase: {phase_name}")

            if result.status != PhaseStatus.ERROR:
                result.status = PhaseStatus.COMPLETE
            result.end_time = datetime.now()

        except Exception as e:
            result.status = PhaseStatus.ERROR
            result.errors.append(str(e))
            result.end_time = datetime.now()
            self.logger.error(f"Phase {phase_name} error: {e}")

        return result

    def _create_training_protocols(self) -> Dict[str, Dict[str, Any]]:
        """Return training protocol presets for major AI families."""
        return {
            "qwen": {
                "output_format": "qwen",
                "prompt": "Please explain this information:",
                "file_extension": ".txt",
                "required_markers": ["<|user|>", "<|assistant|>"],
            },
            "llama2": {
                "output_format": "llama2",
                "prompt": "Please explain this information:",
                "file_extension": ".jsonl",
                "required_markers": ["[INST]", "[/INST]"],
            },
            "alpaca": {
                "output_format": "alpaca",
                "prompt": "Please explain this information:",
                "file_extension": ".txt",
                "required_markers": ["### Instruction:", "### Response:"],
            },
            "chatml": {
                "output_format": "chatml",
                "prompt": "Please explain this information:",
                "file_extension": ".jsonl",
                "required_markers": ["<|im_start|>", "<|im_end|>"],
            },
            "sharegpt": {
                "output_format": "sharegpt",
                "prompt": "Please explain this information:",
                "file_extension": ".jsonl",
                "required_markers": ["human", "gpt"],
            },
            "openai": {
                "output_format": "gpt_jsonl",
                "prompt": "Please explain this information:",
                "file_extension": ".jsonl",
                "required_markers": [
                    '"messages"',
                    '"role": "user"',
                    '"role": "assistant"',
                ],
            },
            "gpt_jsonl": {
                "output_format": "gpt_jsonl",
                "prompt": "Please explain this information:",
                "file_extension": ".jsonl",
                "required_markers": [
                    '"messages"',
                    '"role": "user"',
                    '"role": "assistant"',
                ],
            },
            "claude": {
                "output_format": "instruct",
                "prompt": "Please explain this information:",
                "file_extension": ".txt",
                "required_markers": ["Question:", "Answer:"],
            },
            "mistral": {
                "output_format": "chatml",
                "prompt": "Please explain this information:",
                "file_extension": ".jsonl",
                "required_markers": ["<|im_start|>", "<|im_end|>"],
            },
            "gemma": {
                "output_format": "alpaca",
                "prompt": "Please explain this information:",
                "file_extension": ".txt",
                "required_markers": ["### Instruction:", "### Response:"],
            },
        }

    def _resolve_training_protocol(
        self, phase_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve protocol from settings with safe fallback."""
        protocols = self._create_training_protocols()
        target = str(phase_settings.get("training_target", "qwen")).lower()
        return protocols.get(target, protocols["qwen"])

    def _validate_training_output(
        self, content: str, protocol: Dict[str, Any], strict: bool
    ) -> bool:
        """Validate output markers for selected training protocol."""
        if not strict:
            return True

        if protocol.get("output_format") == "gpt_jsonl":
            try:
                parsed = json.loads(content)
                messages = parsed.get("messages", [])
                if not isinstance(messages, list) or len(messages) < 2:
                    return False
                roles = [m.get("role") for m in messages if isinstance(m, dict)]
                return "user" in roles and "assistant" in roles
            except Exception:
                return False

        for marker in protocol.get("required_markers", []):
            if marker not in content:
                return False
        return True

    def _normalize_personality_name(self, personality: str) -> str:
        """Normalize personality selector values (supports custom:name)."""
        value = str(personality or "professional").strip()
        if value.startswith("custom:"):
            return value.split(":", 1)[1].strip() or "professional"
        return value

    def _to_bytes(self, value: Any, unit: str) -> int:
        """Convert user-specified size to bytes."""
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0
        if numeric <= 0:
            return 0
        unit = (unit or "mb").lower()
        multiplier = {
            "bytes": 1,
            "kb": 1024,
            "mb": 1024 * 1024,
            "gb": 1024 * 1024 * 1024,
        }.get(unit, 1024 * 1024)
        return int(numeric * multiplier)

    def _compress_content(self, text: str, mode: str) -> str:
        """Apply optional lightweight compression/transforms."""
        if (mode or "none") == "minimal_whitespace":
            return re.sub(r"\s+", " ", text).strip()
        return text

    def _fit_to_bytes(self, text: str, max_bytes: int) -> str:
        """Trim text to max bytes while preserving UTF-8 validity."""
        if max_bytes <= 0:
            return text
        encoded = text.encode("utf-8")
        if len(encoded) <= max_bytes:
            return text
        return encoded[:max_bytes].decode("utf-8", errors="ignore")

    def _split_by_size(
        self, text: str, max_bytes: int, preserve_sentences: bool
    ) -> List[str]:
        """Split text into chunks each <= max_bytes."""
        if max_bytes <= 0:
            return [text]

        def split_by_words(value: str) -> List[str]:
            words = value.split()
            parts = []
            current = []
            for word in words:
                candidate = " ".join(current + [word]).strip()
                if candidate and len(candidate.encode("utf-8")) <= max_bytes:
                    current.append(word)
                else:
                    if current:
                        parts.append(" ".join(current).strip())
                    current = [word]
            if current:
                parts.append(" ".join(current).strip())
            return [part for part in parts if part]

        if preserve_sentences:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            parts = []
            current = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                candidate = f"{current} {sentence}".strip() if current else sentence
                if len(candidate.encode("utf-8")) <= max_bytes:
                    current = candidate
                else:
                    if current:
                        parts.append(current)
                    if len(sentence.encode("utf-8")) <= max_bytes:
                        current = sentence
                    else:
                        parts.extend(split_by_words(sentence))
                        current = ""
            if current:
                parts.append(current)
            return [part for part in parts if part]

        return split_by_words(text)

    def _make_summary_fit(self, text: str, max_bytes: int) -> str:
        """Create a compact summary-like clipping that fits max bytes."""
        if max_bytes <= 0:
            return text
        marker = "\n\n[... content clipped due to size cap ...]\n\n"
        encoded_len = len(text.encode("utf-8"))
        if encoded_len <= max_bytes:
            return text
        head_ratio = 0.55
        tail_ratio = 0.35
        approx_chars = max(200, max_bytes // 2)
        head = text[: int(approx_chars * head_ratio)]
        tail = text[-int(approx_chars * tail_ratio) :]
        summarized = f"{head}{marker}{tail}"
        return self._fit_to_bytes(summarized, max_bytes)

    def _build_capped_outputs(
        self,
        cleaned_content: str,
        max_bytes: int,
        strategy: str,
        preserve_sentences: bool,
    ) -> List[str]:
        """Apply capping strategy and return one or more outputs."""
        if max_bytes <= 0:
            return [cleaned_content]
        if len(cleaned_content.encode("utf-8")) <= max_bytes:
            return [cleaned_content]

        strategy = (strategy or "split").lower()
        if strategy == "truncate":
            return [self._fit_to_bytes(cleaned_content, max_bytes)]
        if strategy == "summarize":
            return [self._make_summary_fit(cleaned_content, max_bytes)]
        if strategy == "reject":
            return []
        return self._split_by_size(cleaned_content, max_bytes, preserve_sentences)

    def _sanitize_for_finetuning(
        self,
        text: str,
        enabled: bool,
        normalization_form: str,
        max_blank_lines: int,
    ) -> Dict[str, Any]:
        """Remove problematic Unicode/control artifacts unsafe for finetuning."""
        if not enabled:
            return {
                "text": text,
                "removed_control_chars": 0,
                "removed_invisible_chars": 0,
                "removed_noncharacters": 0,
            }

        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")

        form = (normalization_form or "NFKC").upper()
        if form not in {"NFC", "NFKC", "NFD", "NFKD"}:
            form = "NFKC"
        cleaned = unicodedata.normalize(form, cleaned)

        invisible_and_bidi = {
            "\u200b",  # zero width space
            "\u200c",  # zero width non-joiner
            "\u200d",  # zero width joiner
            "\u2060",  # word joiner
            "\ufeff",  # BOM/ZWNBSP
            "\u202a",  # LRE
            "\u202b",  # RLE
            "\u202c",  # PDF
            "\u202d",  # LRO
            "\u202e",  # RLO
            "\u2066",  # LRI
            "\u2067",  # RLI
            "\u2068",  # FSI
            "\u2069",  # PDI
        }

        normalized_space_map = {
            "\u00a0": " ",  # nbsp
            "\u1680": " ",
            "\u2000": " ",
            "\u2001": " ",
            "\u2002": " ",
            "\u2003": " ",
            "\u2004": " ",
            "\u2005": " ",
            "\u2006": " ",
            "\u2007": " ",
            "\u2008": " ",
            "\u2009": " ",
            "\u200a": " ",
            "\u202f": " ",
            "\u205f": " ",
            "\u3000": " ",
            "\u0009": " ",  # tab -> space
            "\u000b": " ",
            "\u000c": " ",
        }

        removed_control_chars = 0
        removed_invisible_chars = 0
        removed_noncharacters = 0
        out_chars = []

        for ch in cleaned:
            if ch in normalized_space_map:
                out_chars.append(normalized_space_map[ch])
                continue

            if ch in invisible_and_bidi:
                removed_invisible_chars += 1
                continue

            codepoint = ord(ch)
            if (
                0xFDD0 <= codepoint <= 0xFDEF
                or (codepoint & 0xFFFE) == 0xFFFE
                or 0xE000 <= codepoint <= 0xF8FF
            ):
                removed_noncharacters += 1
                continue

            category = unicodedata.category(ch)
            if category in {"Cc", "Cf", "Cs", "Co", "Cn"} and ch != "\n":
                removed_control_chars += 1
                continue

            if ch == "\ufffd":
                removed_noncharacters += 1
                continue

            out_chars.append(ch)

        cleaned = "".join(out_chars)
        cleaned = cleaned.encode("utf-8", errors="ignore").decode(
            "utf-8", errors="ignore"
        )
        cleaned = re.sub(r"[^\S\n]+", " ", cleaned)
        cleaned = "\n".join(line.rstrip() for line in cleaned.split("\n"))

        max_blank = max(1, int(max_blank_lines or 2))
        cleaned = re.sub(r"\n{" + str(max_blank + 1) + r",}", "\n" * max_blank, cleaned)
        cleaned = cleaned.strip()

        return {
            "text": cleaned,
            "removed_control_chars": removed_control_chars,
            "removed_invisible_chars": removed_invisible_chars,
            "removed_noncharacters": removed_noncharacters,
        }

    def _parse_phase_status(self, status_value: Any) -> PhaseStatus:
        """Parse persisted phase status across multiple serialization styles."""
        if isinstance(status_value, PhaseStatus):
            return status_value
        if not isinstance(status_value, str):
            return PhaseStatus.ENABLED

        normalized = status_value.strip()
        if normalized.startswith("PhaseStatus."):
            normalized = normalized.split(".", 1)[1]

        enum_lookup = {
            "ENABLED": PhaseStatus.ENABLED,
            "DISABLED": PhaseStatus.DISABLED,
            "RUNNING": PhaseStatus.RUNNING,
            "COMPLETE": PhaseStatus.COMPLETE,
            "ERROR": PhaseStatus.ERROR,
            "green": PhaseStatus.ENABLED,
            "red": PhaseStatus.DISABLED,
            "yellow": PhaseStatus.RUNNING,
            "blue": PhaseStatus.COMPLETE,
            "orange": PhaseStatus.ERROR,
        }

        return enum_lookup.get(
            normalized, enum_lookup.get(normalized.upper(), PhaseStatus.ENABLED)
        )

    def _execute_phase1(self, config: PhaseConfig, result: PhaseResult) -> PhaseResult:
        """Execute Phase 1: Input Parsing & Sanitization."""
        # Use existing components
        try:
            from data_sanitizer import DataSanitizer
        except ImportError:
            # Fallback to basic sanitization
            DataSanitizer = None

        try:
            from file_processors import create_file_processor
            from pipeline_orchestrator import PipelineConfig
        except ImportError:
            # Fallback to basic text extraction
            create_file_processor = None
            PipelineConfig = None

        input_path = Path(config.input_folder)
        output_path = Path(config.output_folder)
        output_path.mkdir(exist_ok=True)

        self.logger.info(
            f"Phase 1: Processing files from {input_path} to {output_path}"
        )

        # Initialize sanitizer if available
        if DataSanitizer:
            sanitizer = DataSanitizer(config.settings.get("security_level", "balanced"))
        else:
            sanitizer = None

        # Process all supported file types
        supported_extensions = [".pdf", ".csv", ".json", ".jsonl", ".txt", ".md"]
        capped_files = 0
        capped_parts_written = 0

        max_size_unit = str(config.settings.get("size_cap_unit", "mb")).lower()
        max_clean_file_size_bytes = self._to_bytes(
            config.settings.get("max_clean_file_size_mb", 0), max_size_unit
        )
        size_cap_strategy = str(
            config.settings.get("size_cap_strategy", "split")
        ).lower()
        preserve_sentence_boundaries = bool(
            config.settings.get("preserve_sentence_boundaries", True)
        )
        compression_mode = str(config.settings.get("compression_mode", "none")).lower()
        on_cap_exceeded = str(config.settings.get("on_cap_exceeded", "warn")).lower()
        recursive_scan = bool(config.settings.get("recursive_input_scan", False))
        min_clean_chars = int(config.settings.get("min_clean_chars", 1) or 1)
        drop_empty_outputs = bool(config.settings.get("drop_empty_outputs", True))
        finetune_safe_cleaning = bool(
            config.settings.get("finetune_safe_cleaning", True)
        )
        unicode_normalization_form = str(
            config.settings.get("unicode_normalization_form", "NFKC")
        )
        max_consecutive_blank_lines = int(
            config.settings.get("max_consecutive_blank_lines", 2) or 2
        )

        removed_control_total = 0
        removed_invisible_total = 0
        removed_noncharacters_total = 0

        input_iterator = (
            input_path.rglob("*") if recursive_scan else input_path.glob("*")
        )

        for file_path in input_iterator:
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    # Extract text content
                    if create_file_processor and PipelineConfig:
                        pipeline_config = PipelineConfig()
                        processor = create_file_processor(file_path, pipeline_config)
                    else:
                        processor = None

                    if processor:
                        segments = processor.extract_text_segments(file_path)
                        content = "\n\n".join(segments)
                    else:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()

                    # Sanitize content if sanitizer available
                    if sanitizer:
                        sanitized_result = sanitizer.sanitize_text(content)
                        cleaned_content = sanitized_result.cleaned_text
                    else:
                        # Basic cleaning
                        cleaned_content = content.strip()
                        # Remove common problematic characters
                        cleaned_content = cleaned_content.replace(
                            "\x00", ""
                        )  # Null bytes
                        cleaned_content = cleaned_content.replace("\ufeff", "")  # BOM

                    cleaned_content = self._compress_content(
                        cleaned_content, compression_mode
                    )

                    sanitization_result = self._sanitize_for_finetuning(
                        cleaned_content,
                        enabled=finetune_safe_cleaning,
                        normalization_form=unicode_normalization_form,
                        max_blank_lines=max_consecutive_blank_lines,
                    )
                    cleaned_content = sanitization_result["text"]
                    removed_control_total += sanitization_result[
                        "removed_control_chars"
                    ]
                    removed_invisible_total += sanitization_result[
                        "removed_invisible_chars"
                    ]
                    removed_noncharacters_total += sanitization_result[
                        "removed_noncharacters"
                    ]

                    if (
                        drop_empty_outputs
                        and len(cleaned_content.strip()) < min_clean_chars
                    ):
                        self.logger.warning(
                            f"Phase 1: Skipping {file_path.name} after cleaning (below min chars: {min_clean_chars})"
                        )
                        result.files_failed += 1
                        result.errors.append(
                            f"Skipped {file_path.name}: cleaned content below min chars ({min_clean_chars})"
                        )
                        continue

                    # Apply optional size cap after cleaning
                    encoded_size = len(cleaned_content.encode("utf-8"))
                    if (
                        max_clean_file_size_bytes
                        and encoded_size > max_clean_file_size_bytes
                    ):
                        capped_files += 1
                        if on_cap_exceeded == "fail":
                            raise ValueError(
                                f"Cleaned file exceeds size cap ({encoded_size} > {max_clean_file_size_bytes} bytes)"
                            )
                        if on_cap_exceeded == "quarantine":
                            quarantine_dir = output_path / "quarantine"
                            quarantine_dir.mkdir(exist_ok=True)
                            quarantine_file = (
                                quarantine_dir / f"{file_path.stem}_oversized.txt"
                            )
                            with open(quarantine_file, "w", encoding="utf-8") as f:
                                f.write(cleaned_content)
                            result.files_failed += 1
                            result.errors.append(
                                f"Oversized cleaned file quarantined: {file_path.name} ({encoded_size} bytes)"
                            )
                            self.logger.warning(
                                f"Phase 1: Quarantined oversized cleaned file {file_path.name}"
                            )
                            continue

                    output_texts = self._build_capped_outputs(
                        cleaned_content,
                        max_clean_file_size_bytes,
                        size_cap_strategy,
                        preserve_sentence_boundaries,
                    )

                    if not output_texts:
                        raise ValueError(
                            f"Size cap strategy '{size_cap_strategy}' produced no output for {file_path.name}"
                        )

                    # Save sanitized/capped text to Phase 1 folder
                    written_files = []
                    for idx, output_text in enumerate(output_texts, 1):
                        suffix = "" if len(output_texts) == 1 else f"_part{idx:03d}"
                        output_file = (
                            output_path / f"{file_path.stem}_sanitized{suffix}.txt"
                        )
                        with open(output_file, "w", encoding="utf-8") as f:
                            f.write(output_text)
                        written_files.append(output_file)
                        result.output_files.append(str(output_file))

                    if len(written_files) > 1 or (
                        max_clean_file_size_bytes
                        and encoded_size > max_clean_file_size_bytes
                    ):
                        capped_parts_written += len(written_files)
                        manifest = {
                            "original_file": str(file_path),
                            "size_cap_bytes": max_clean_file_size_bytes,
                            "original_cleaned_size_bytes": encoded_size,
                            "strategy": size_cap_strategy,
                            "parts": [
                                {"file": str(part), "size_bytes": part.stat().st_size}
                                for part in written_files
                            ],
                        }
                        manifest_file = (
                            output_path / f"{file_path.stem}_size_cap_manifest.json"
                        )
                        with open(manifest_file, "w", encoding="utf-8") as f:
                            json.dump(manifest, f, indent=2)
                        result.output_files.append(str(manifest_file))

                    result.files_processed += 1
                    self.logger.info(
                        f"Phase 1: Processed {file_path.name} -> {len(written_files)} output file(s)"
                    )

                except Exception as e:
                    error_msg = f"Error processing {file_path}: {e}"
                    result.errors.append(error_msg)
                    result.files_failed += 1
                    self.logger.error(error_msg)

        result.metrics = {
            "files_processed": result.files_processed,
            "files_failed": result.files_failed,
            "size_cap_enabled": max_clean_file_size_bytes > 0,
            "size_cap_bytes": max_clean_file_size_bytes,
            "size_cap_strategy": size_cap_strategy,
            "capped_files": capped_files,
            "capped_parts_written": capped_parts_written,
            "recursive_input_scan": recursive_scan,
            "min_clean_chars": min_clean_chars,
            "drop_empty_outputs": drop_empty_outputs,
            "finetune_safe_cleaning": finetune_safe_cleaning,
            "unicode_normalization_form": unicode_normalization_form,
            "max_consecutive_blank_lines": max_consecutive_blank_lines,
            "removed_control_chars_total": removed_control_total,
            "removed_invisible_chars_total": removed_invisible_total,
            "removed_noncharacters_total": removed_noncharacters_total,
            "output_folder": str(output_path),
            "transfer_status": f"Data transferred from {input_path} to {output_path}",
        }

        self.logger.info(
            f"Phase 1 Complete: {result.files_processed} files processed, data transferred to Phase 1 folder"
        )
        return result

    def _execute_phase2(self, config: PhaseConfig, result: PhaseResult) -> PhaseResult:
        """Execute Phase 2: Chunking & Fact Extraction."""
        try:
            from text_chunker import AdvancedChunker
        except ImportError:
            # Fallback to basic chunking
            AdvancedChunker = None

        input_path = Path(config.input_folder)  # Phase 1 folder
        output_path = Path(config.output_folder)  # Phase 2 folder
        output_path.mkdir(exist_ok=True)

        self.logger.info(
            f"Phase 2: Processing chunks from {input_path} to {output_path}"
        )

        # Initialize chunker
        if AdvancedChunker:
            chunker = AdvancedChunker(
                chunk_size=config.settings.get("max_chunk_tokens", 150),
                overlap=config.settings.get("token_overlap", 1),
            )
        else:
            chunker = None

        # Process all text files from Phase 1
        for file_path in input_path.glob("*.txt"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Create subfolder for this file in Phase 2
                if config.settings.get("create_subfolders", True):
                    file_output_path = output_path / file_path.stem
                    file_output_path.mkdir(exist_ok=True)
                else:
                    file_output_path = output_path

                # Chunk the content
                if chunker:
                    chunks = chunker.chunk_text(content)
                else:
                    # Basic chunking - split by sentences
                    sentences = content.split(". ")
                    chunks = []
                    current_chunk = ""
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) < 500:  # Basic size limit
                            current_chunk += sentence + ". "
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence + ". "
                    if current_chunk:
                        chunks.append(current_chunk.strip())

                # Save chunks to Phase 2 folder
                for i, chunk in enumerate(chunks):
                    chunk_file = file_output_path / f"chunk_{i:03d}.txt"
                    with open(chunk_file, "w", encoding="utf-8") as f:
                        f.write(chunk)

                    result.output_files.append(str(chunk_file))

                result.files_processed += 1
                self.logger.info(
                    f"Phase 2: Chunked {file_path.name} into {len(chunks)} chunks → {file_output_path}"
                )

            except Exception as e:
                error_msg = f"Error chunking {file_path}: {e}"
                result.errors.append(error_msg)
                result.files_failed += 1
                self.logger.error(error_msg)

        result.metrics = {
            "total_chunks": len(result.output_files),
            "files_processed": result.files_processed,
            "average_chunks_per_file": len(result.output_files)
            / max(result.files_processed, 1),
            "output_folder": str(output_path),
            "transfer_status": f"Data transferred from {input_path} to {output_path}",
        }

        self.logger.info(
            f"Phase 2 Complete: {len(result.output_files)} chunks created, data transferred to Phase 2 folder"
        )
        return result

    def _execute_phase3(self, config: PhaseConfig, result: PhaseResult) -> PhaseResult:
        """Execute Phase 3: Personality Prompting & Formatting with Enhanced Accuracy."""
        try:
            from enhanced_conversation_formatter import get_enhanced_formatter

            use_enhanced = True
        except ImportError:
            use_enhanced = False
            try:
                from personality_modifier import PersonalityModifier
            except ImportError:
                PersonalityModifier = None

            try:
                from conversation_formatter import ConversationFormatter
            except ImportError:
                ConversationFormatter = None

        try:
            from personality_modifier import PersonalityModifier
        except ImportError:
            PersonalityModifier = None

        input_path = Path(config.input_folder)  # Phase 2 folder
        output_path = Path(config.output_folder)  # Phase 3 folder
        output_path.mkdir(exist_ok=True)

        self.logger.info(
            f"Phase 3: Processing personality formatting from {input_path} to {output_path}"
        )

        personality_modifier = None
        formatter = None

        selected_personality = config.settings.get(
            "personality_template", "professional"
        )
        personality = self._normalize_personality_name(selected_personality)
        strength = config.settings.get("personality_strength", 0.7)
        protocol = self._resolve_training_protocol(config.settings)
        output_format = protocol.get(
            "output_format", config.settings.get("output_format", "qwen")
        )
        emit_combined_jsonl = bool(config.settings.get("emit_combined_jsonl", True))
        combined_jsonl_filename = (
            str(
                config.settings.get("combined_jsonl_filename", "chatgpt_training.jsonl")
            ).strip()
            or "chatgpt_training.jsonl"
        )
        strict_role_validation = bool(
            config.settings.get("strict_role_validation", True)
        )
        protocol_prompt = protocol.get("prompt", "Please explain this information:")
        combined_jsonl_lines = []

        # Initialize enhanced formatter if available
        enhanced_formatter = None
        if use_enhanced:
            try:
                enhanced_formatter = get_enhanced_formatter(
                    output_format, target_accuracy=95.0
                )
                self.logger.info(
                    "Using enhanced conversation formatter with 95% accuracy validation"
                )
            except Exception as e:
                enhanced_formatter = None
                self.logger.warning(
                    f"Enhanced formatter unavailable ({e}); falling back to standard formatting"
                )

        if PersonalityModifier:
            try:
                personality_modifier = PersonalityModifier()
            except Exception as e:
                personality_modifier = None
                self.logger.warning(
                    f"Personality modifier unavailable ({e}); using formatter-only personality"
                )

        # Process all chunk files from Phase 2
        for chunk_file in input_path.rglob("*.txt"):
            try:
                with open(chunk_file, "r", encoding="utf-8") as f:
                    content = f.read()

                transformed_content = content
                if personality_modifier:
                    try:
                        personality_result = personality_modifier.apply_personality(
                            content, personality, strength
                        )
                        transformed_content = personality_result.modified_text
                    except Exception as e:
                        self.logger.warning(
                            f"Personality pre-transform failed for {chunk_file.name}: {e}"
                        )

                # Use enhanced formatter for 95% accuracy
                if enhanced_formatter:
                    try:
                        formatting_result = (
                            enhanced_formatter.format_conversation_enhanced(
                                user_input=protocol_prompt,
                                assistant_response=transformed_content,
                                personality=personality,
                                context=f"Source file: {chunk_file.name}",
                            )
                        )

                        formatted_content = formatting_result.formatted_content

                        # Log accuracy metrics
                        if formatting_result.accuracy_score >= 95.0:
                            self.logger.info(
                                f"Enhanced formatting successful: {formatting_result.accuracy_score:.1f}% accuracy"
                            )
                        else:
                            self.logger.warning(
                                f"Enhanced formatting below target: {formatting_result.accuracy_score:.1f}% accuracy"
                            )

                    except Exception as e:
                        self.logger.error(
                            f"Enhanced formatting failed: {e}, falling back to standard"
                        )
                        formatted_content = self._fallback_formatting(
                            transformed_content, output_format, personality
                        )

                else:
                    # Fallback to standard formatting
                    formatted_content = self._fallback_formatting(
                        transformed_content, output_format, personality
                    )

                if not self._validate_training_output(
                    formatted_content, protocol, strict_role_validation
                ):
                    raise ValueError(
                        f"Output failed protocol validation for target '{config.settings.get('training_target', 'qwen')}'"
                    )

                # Save formatted content to Phase 3 folder
                relative_path = chunk_file.relative_to(input_path)
                if output_format in ["qwen", "alpaca", "instruct"]:
                    output_file = output_path / relative_path.with_suffix(".txt")
                else:
                    output_file = output_path / relative_path.with_suffix(".jsonl")

                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(formatted_content)

                if output_format == "gpt_jsonl" and emit_combined_jsonl:
                    parsed = json.loads(formatted_content)
                    combined_jsonl_lines.append(json.dumps(parsed, ensure_ascii=False))

                result.output_files.append(str(output_file))
                result.files_processed += 1
                self.logger.info(
                    f"Phase 3: Applied {personality} personality to {chunk_file.name} → {output_file.name}"
                )

            except Exception as e:
                error_msg = f"Error processing {chunk_file}: {e}"
                result.errors.append(error_msg)
                result.files_failed += 1
                self.logger.error(error_msg)

        if (
            output_format == "gpt_jsonl"
            and emit_combined_jsonl
            and combined_jsonl_lines
        ):
            combined_file = output_path / combined_jsonl_filename
            with open(combined_file, "w", encoding="utf-8") as f:
                f.write("\n".join(combined_jsonl_lines) + "\n")
            result.output_files.append(str(combined_file))
            self.logger.info(
                f"Phase 3: Wrote combined GPT JSONL dataset with {len(combined_jsonl_lines)} records -> {combined_file.name}"
            )

        result.metrics = {
            "personality_selected": selected_personality,
            "personality_applied": personality,
            "strength_used": strength,
            "training_target": config.settings.get("training_target", "qwen"),
            "emit_combined_jsonl": emit_combined_jsonl,
            "combined_jsonl_records": len(combined_jsonl_lines),
            "format": output_format,
            "files_processed": result.files_processed,
            "output_folder": str(output_path),
            "transfer_status": f"Data transferred from {input_path} to {output_path}",
        }

        self.logger.info(
            f"Phase 3 Complete: {result.files_processed} files formatted with {personality} personality, data transferred to Phase 3 folder"
        )
        return result

    def _fallback_formatting(
        self, content: str, output_format: str, personality: str
    ) -> str:
        """Fallback formatting method when enhanced formatter is not available."""
        # Apply basic personality transformation
        if personality == "casual":
            content = content.replace("do not", "don't").replace("cannot", "can't")
            content = content.replace("It is", "It's").replace("You are", "You're")
        elif personality == "formal":
            content = content.replace("don't", "do not").replace("can't", "cannot")
            content = content.replace("It's", "It is").replace("You're", "You are")
        elif personality == "friendly":
            content = f"Hey there! {content} Hope this helps!"
        elif personality == "technical":
            content = f"Technical analysis: {content}"

        # Apply format-specific formatting
        if output_format == "qwen":
            return (
                f"<|user|>\nPlease explain this information:\n<|assistant|>\n{content}"
            )
        elif output_format == "alpaca":
            return f"### Instruction:\nPlease explain this information:\n\n### Response:\n{content}"
        elif output_format == "chatml":
            return f"<|im_start|>user\nPlease explain this information:\n<|im_end|>\n<|im_start|>assistant\n{content}\n<|im_end|>"
        elif output_format == "sharegpt":
            import json

            return json.dumps(
                [
                    {"from": "human", "value": "Please explain this information:"},
                    {"from": "gpt", "value": content},
                ]
            )
        elif output_format == "gpt_jsonl":
            import json

            return json.dumps(
                {
                    "messages": [
                        {"role": "user", "content": "Please explain this information:"},
                        {"role": "assistant", "content": content},
                    ]
                },
                ensure_ascii=False,
            )
        elif output_format == "llama2":
            return f"[INST] Please explain this information: [/INST] {content}"
        elif output_format == "instruct":
            return f"Question: Please explain this information:\n\nAnswer: {content}"
        else:
            # Default to qwen format
            return (
                f"<|user|>\nPlease explain this information:\n<|assistant|>\n{content}"
            )

    def _execute_phase4(self, config: PhaseConfig, result: PhaseResult) -> PhaseResult:
        """Execute Phase 4: Quality Scoring & Assessment."""
        try:
            from quality_scorer import LLMQualityScorer
        except ImportError:
            LLMQualityScorer = None

        input_path = Path(config.input_folder)  # Phase 3 folder
        output_path = Path(config.output_folder)  # Phase 4 folder
        output_path.mkdir(exist_ok=True)

        self.logger.info(
            f"Phase 4: Quality scoring and assessment from {input_path} to {output_path}"
        )

        # Initialize enhanced scorer if available
        if LLMQualityScorer:
            scorer = LLMQualityScorer(
                model=config.settings.get("scoring_model", "gpt-4o"),
                metrics=config.settings.get(
                    "quality_metrics",
                    [
                        "factual_accuracy",
                        "format_compliance",
                        "content_preservation",
                        "instruction_following",
                        "consistency",
                        "completeness",
                    ],
                ),
                target_accuracy=95.0,  # Enhanced accuracy requirement
            )
        else:
            scorer = None

        # Find all files from Phase 3 (various formats)
        all_files = []
        for pattern in ["*.jsonl", "*.txt", "*.json"]:
            all_files.extend(input_path.rglob(pattern))

        if not all_files:
            self.logger.warning(f"No files found in Phase 3 folder: {input_path}")
            return result

        # Sample files for scoring
        sample_percentage = config.settings.get("sample_percentage", 10) / 100
        sample_size = max(1, int(len(all_files) * sample_percentage))
        sample_files = all_files[:sample_size]

        self.logger.info(
            f"Phase 4: Scoring {len(sample_files)} files ({sample_percentage * 100:.1f}% of {len(all_files)} total)"
        )

        scores = []
        total_quality_score = 0

        for file_path in sample_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Score the content
                if scorer:
                    score_result = scorer.score_content(content)
                    scores.append(
                        {
                            "file": str(file_path.relative_to(input_path)),
                            "overall_score": score_result.overall_score,
                            "accuracy": score_result.accuracy_score,
                            "fluency": score_result.fluency_score,
                            "personality_depth": score_result.personality_depth_score,
                            "coherence": score_result.coherence_score,
                            "training_readiness": score_result.training_readiness_score,
                            "feedback": score_result.feedback,
                            "confidence": score_result.confidence,
                            "cost": score_result.cost,
                        }
                    )
                    total_quality_score += score_result.overall_score
                else:
                    # Basic quality assessment (fallback)
                    word_count = len(content.split())
                    basic_score = min(100, max(0, 50 + (word_count - 50) * 0.2))
                    scores.append(
                        {
                            "file": str(file_path.relative_to(input_path)),
                            "overall_score": basic_score,
                            "accuracy": basic_score,
                            "fluency": basic_score,
                            "personality_depth": 50,
                            "coherence": basic_score,
                            "training_readiness": basic_score,
                            "feedback": "Basic rule-based scoring (AI not available)",
                            "confidence": 0.5,
                            "cost": 0.0,
                        }
                    )
                    total_quality_score += basic_score

                result.files_processed += 1
                self.logger.info(
                    f"Phase 4: Scored {file_path.name} - Quality: {scores[-1]['overall_score']:.1f}"
                )

            except Exception as e:
                error_msg = f"Error scoring {file_path}: {e}"
                result.errors.append(error_msg)
                result.files_failed += 1
                self.logger.error(error_msg)

        # Calculate average quality
        average_quality = total_quality_score / max(len(scores), 1)

        # Generate comprehensive report in Phase 4 folder
        if config.settings.get("generate_report", True):
            report_file = output_path / "quality_assessment_report.json"

            # Create detailed report
            report_data = {
                "pipeline_summary": {
                    "total_files_in_phase3": len(all_files),
                    "files_sampled": len(sample_files),
                    "sample_percentage": config.settings.get("sample_percentage", 10),
                    "files_scored": result.files_processed,
                    "files_failed": result.files_failed,
                    "average_quality_score": average_quality,
                    "processing_complete": True,
                },
                "quality_metrics": {
                    "overall_grade": self._assign_quality_grade(average_quality),
                    "average_scores": self._calculate_average_scores(scores),
                    "recommendations": self._generate_recommendations(
                        average_quality, scores
                    ),
                },
                "detailed_scores": scores,
                "processing_info": {
                    "generated_at": datetime.now().isoformat(),
                    "scoring_model": config.settings.get("scoring_model", "rule-based"),
                    "input_folder": str(input_path),
                    "output_folder": str(output_path),
                    "total_cost": sum(score.get("cost", 0) for score in scores),
                },
            }

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)

            result.output_files.append(str(report_file))

            # Also create a summary file
            summary_file = output_path / "pipeline_summary.txt"
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(f"LLM Data Pipeline - Final Quality Assessment\n")
                f.write(f"=" * 50 + "\n\n")
                f.write(
                    f"Processing Complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                )
                f.write(f"Files Processed: {len(all_files)} total files\n")
                f.write(
                    f"Quality Score: {average_quality:.1f}/100 ({self._assign_quality_grade(average_quality)})\n"
                )
                f.write(
                    f"Sample Size: {len(sample_files)} files ({sample_percentage * 100:.1f}%)\n\n"
                )
                f.write(f"Data Flow:\n")
                f.write(f"  Input → Phase 1 → Phase 2 → Phase 3 → Phase 4 ✓\n\n")
                f.write(f"Final Output Location: {output_path}\n")
                f.write(f"Quality Report: {report_file.name}\n")

            result.output_files.append(str(summary_file))

        result.metrics = {
            "files_sampled": len(sample_files),
            "sample_percentage": config.settings.get("sample_percentage", 10),
            "average_quality_score": average_quality,
            "quality_grade": self._assign_quality_grade(average_quality),
            "report_generated": config.settings.get("generate_report", True),
            "output_folder": str(output_path),
            "transfer_status": f"Final assessment completed - data in {output_path}",
            "pipeline_complete": True,
        }

        self.logger.info(
            f"Phase 4 Complete: Quality assessment finished - Average score: {average_quality:.1f}/100, Final data in Phase 4 folder"
        )
        return result

    def _assign_quality_grade(self, score: float) -> str:
        """Assign letter grade based on quality score."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _calculate_average_scores(self, scores: List[Dict]) -> Dict[str, float]:
        """Calculate average scores across all metrics."""
        if not scores:
            return {}

        metrics = [
            "overall_score",
            "accuracy",
            "fluency",
            "personality_depth",
            "coherence",
            "training_readiness",
        ]
        averages = {}

        for metric in metrics:
            values = [score.get(metric, 0) for score in scores]
            averages[metric] = sum(values) / len(values)

        return averages

    def _generate_recommendations(
        self, average_quality: float, scores: List[Dict]
    ) -> List[str]:
        """Generate recommendations based on quality scores."""
        recommendations = []

        if average_quality >= 85:
            recommendations.append("Excellent quality! Data is ready for LLM training.")
        elif average_quality >= 70:
            recommendations.append("Good quality with minor improvements possible.")
        else:
            recommendations.append("Consider improving data quality before training.")

        # Check specific metrics
        if scores:
            avg_scores = self._calculate_average_scores(scores)

            if avg_scores.get("accuracy", 0) < 70:
                recommendations.append(
                    "Consider fact-checking and improving content accuracy."
                )

            if avg_scores.get("personality_depth", 0) < 60:
                recommendations.append("Strengthen personality voice and consistency.")

            if avg_scores.get("training_readiness", 0) < 70:
                recommendations.append(
                    "Optimize content format and length for training."
                )

        return recommendations

    def pause_pipeline(self):
        """Pause pipeline execution."""
        self.pause_requested = True
        self.logger.info("Pipeline pause requested")

    def resume_pipeline(self):
        """Resume pipeline execution."""
        self.pause_requested = False
        self.logger.info("Pipeline resumed")

    def abort_pipeline(self):
        """Abort pipeline execution."""
        self.abort_requested = True
        self.logger.info("Pipeline abort requested")

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "is_running": self.is_running,
            "current_phase": self.current_phase,
            "pause_requested": self.pause_requested,
            "abort_requested": self.abort_requested,
            "phases": {
                name: {"status": config.status.value, "description": config.description}
                for name, config in self.phases.items()
            },
            "results": {name: asdict(result) for name, result in self.results.items()},
        }

    def save_configuration(self):
        """Save current phase configuration."""
        config_data = {name: asdict(config) for name, config in self.phases.items()}
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, default=str)

    def load_configuration(self):
        """Load phase configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                for name, data in config_data.items():
                    if name in self.phases:
                        status_value = data.get("status", "green")
                        self.phases[name].status = self._parse_phase_status(
                            status_value
                        )

                        self.phases[name].settings.update(data.get("settings", {}))

                self.logger.info("Configuration loaded successfully")

            except Exception as e:
                self.logger.error(f"Error loading configuration: {e}")


# Global pipeline instance
_pipeline_instance = None


def get_pipeline() -> PhaseControlledPipeline:
    """Get the global pipeline instance."""
    global _pipeline_instance

    if _pipeline_instance is None:
        _pipeline_instance = PhaseControlledPipeline()

    return _pipeline_instance
