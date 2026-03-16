#!/usr/bin/env python3
"""
Environment configuration system for the AI-enhanced pipeline.
Loads all settings from .env file for easy configuration management.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging


@dataclass
class EnvironmentConfig:
    """Complete environment configuration loaded from .env file."""

    # OpenAI API Settings
    openai_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: Optional[str] = None
    openrouter_app_name: str = "AI Data Pipeline"
    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.3
    openai_max_tokens: int = 1000
    openai_timeout: int = 30

    # Cost Control
    daily_cost_limit: float = 20.0
    cost_per_request_limit: float = 0.10
    enable_cost_alerts: bool = True

    # AI Features
    enable_ai_classification: bool = True
    enable_content_enhancement: bool = True
    enable_smart_segmentation: bool = True
    ai_confidence_threshold: float = 0.8
    enhancement_quality_threshold: float = 0.7

    # Caching Settings
    enable_caching: bool = True
    cache_duration_hours: int = 24
    cache_cleanup_interval: int = 168  # 1 week
    max_cache_size_mb: int = 500

    # Rate Limiting
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 3000
    max_requests_per_day: int = 10000

    # Security Settings
    enable_security_filtering: bool = True
    security_level: str = "balanced"  # permissive, balanced, strict, paranoid
    quarantine_enabled: bool = True

    # Pipeline Settings
    input_folder: str = "input"
    filtered_folder: str = "filtered"
    output_folder: str = "output"
    error_folder: str = "errors"
    archive_folder: str = "archive"

    # Processing Settings
    output_format: str = "qwen"
    parallel_processing: bool = True
    max_workers: int = 4
    batch_size: int = 10
    processing_interval: float = 5.0
    auto_move_files: bool = True

    # File Monitoring
    watch_input_folder: bool = True
    file_check_interval: float = 2.0
    max_file_size_mb: int = 100

    # Logging Settings
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_max_size_mb: int = 10
    log_file_backup_count: int = 5

    # Database Settings
    database_url: str = "sqlite:///pipeline.db"
    enable_database_logging: bool = True

    # Notification Settings
    enable_notifications: bool = False
    notification_webhook_url: Optional[str] = None
    notification_email: Optional[str] = None

    # Advanced AI Settings
    use_function_calling: bool = False
    enable_streaming: bool = False
    custom_system_prompt: Optional[str] = None

    # Model Fallback Settings
    fallback_model: str = "gpt-3.5-turbo"
    enable_model_fallback: bool = True
    fallback_on_error: bool = True
    fallback_on_cost_limit: bool = True

    # Content Enhancement Settings
    auto_enhance_grammar: bool = True
    auto_enhance_clarity: bool = False
    auto_enhance_structure: bool = False
    preserve_original_meaning: bool = True
    enhancement_batch_size: int = 5

    # Personality Modification Settings
    enable_personality_modifier: bool = True
    personality_template: str = "neutral"
    personality_strength: float = 0.7
    custom_personality_description: Optional[str] = None
    custom_personalities: Dict[str, str] = None
    personality_preserve_meaning: bool = True
    personality_min_confidence: float = 0.6
    personality_cache_enabled: bool = True
    personality_fallback_to_rules: bool = True


class EnvironmentConfigLoader:
    """Loads configuration from .env file and environment variables."""

    def __init__(self, env_file: str = ".env"):
        self.env_file = Path(env_file)
        self.logger = logging.getLogger(__name__)

        # Load .env file if it exists
        self._load_env_file()

    def _load_env_file(self):
        """Load environment variables from .env file."""
        if not self.env_file.exists():
            self.logger.info(
                f"No .env file found at {self.env_file}. Using environment variables and defaults."
            )
            return

        try:
            with open(self.env_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse key=value pairs
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]

                        # Set environment variable
                        os.environ[key] = value

                    else:
                        self.logger.warning(
                            f"Invalid line {line_num} in .env file: {line}"
                        )

            self.logger.info(f"Loaded configuration from {self.env_file}")

        except Exception as e:
            self.logger.error(f"Error loading .env file: {e}")

    def load_config(self) -> EnvironmentConfig:
        """Load complete configuration from environment variables."""
        config = EnvironmentConfig()

        # AI Provider Settings
        provider_alias = os.getenv("OPENAI_PROVIDER") or os.getenv("PROVIDER")
        if provider_alias:
            provider_alias = provider_alias.lower()
            if provider_alias in ["openai", "openrouter"]:
                config.openai_provider = provider_alias
        config.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        config.openrouter_base_url = os.getenv(
            "OPENROUTER_BASE_URL", config.openrouter_base_url
        )
        config.openrouter_site_url = os.getenv("OPENROUTER_SITE_URL")
        config.openrouter_app_name = os.getenv(
            "OPENROUTER_APP_NAME", config.openrouter_app_name
        )
        config.lmstudio_base_url = os.getenv(
            "LMSTUDIO_BASE_URL", config.lmstudio_base_url
        )
        config.ollama_base_url = os.getenv("OLLAMA_BASE_URL", config.ollama_base_url)

        # API key selection (provider-aware)
        if config.openai_provider == "openrouter":
            config.openai_api_key = config.openrouter_api_key or os.getenv(
                "OPENAI_API_KEY"
            )
        elif config.openai_provider in ["lmstudio", "ollama"]:
            config.openai_api_key = os.getenv("OPENAI_API_KEY") or "local-provider"
        else:
            config.openai_api_key = os.getenv("OPENAI_API_KEY")

        placeholder_markers = ["<", "YOUR_", "SET_", "PLACEHOLDER"]
        if config.openai_api_key and any(
            marker in config.openai_api_key for marker in placeholder_markers
        ):
            config.openai_api_key = None
        if config.openrouter_api_key and any(
            marker in config.openrouter_api_key for marker in placeholder_markers
        ):
            config.openrouter_api_key = None

        # OpenAI API Settings
        config.openai_model = os.getenv("OPENAI_MODEL", config.openai_model)
        config.openai_temperature = self._get_float(
            "OPENAI_TEMPERATURE", config.openai_temperature
        )
        config.openai_max_tokens = self._get_int(
            "OPENAI_MAX_TOKENS", config.openai_max_tokens
        )
        config.openai_timeout = self._get_int("OPENAI_TIMEOUT", config.openai_timeout)

        # Cost Control
        config.daily_cost_limit = self._get_float(
            "DAILY_COST_LIMIT", config.daily_cost_limit
        )
        config.cost_per_request_limit = self._get_float(
            "COST_PER_REQUEST_LIMIT", config.cost_per_request_limit
        )
        config.enable_cost_alerts = self._get_bool(
            "ENABLE_COST_ALERTS", config.enable_cost_alerts
        )

        # AI Features
        config.enable_ai_classification = self._get_bool(
            "ENABLE_AI_CLASSIFICATION", config.enable_ai_classification
        )
        config.enable_content_enhancement = self._get_bool(
            "ENABLE_CONTENT_ENHANCEMENT", config.enable_content_enhancement
        )
        config.enable_smart_segmentation = self._get_bool(
            "ENABLE_SMART_SEGMENTATION", config.enable_smart_segmentation
        )
        config.ai_confidence_threshold = self._get_float(
            "AI_CONFIDENCE_THRESHOLD", config.ai_confidence_threshold
        )
        config.enhancement_quality_threshold = self._get_float(
            "ENHANCEMENT_QUALITY_THRESHOLD", config.enhancement_quality_threshold
        )

        # Caching Settings
        config.enable_caching = self._get_bool("ENABLE_CACHING", config.enable_caching)
        config.cache_duration_hours = self._get_int(
            "CACHE_DURATION_HOURS", config.cache_duration_hours
        )
        config.cache_cleanup_interval = self._get_int(
            "CACHE_CLEANUP_INTERVAL", config.cache_cleanup_interval
        )
        config.max_cache_size_mb = self._get_int(
            "MAX_CACHE_SIZE_MB", config.max_cache_size_mb
        )

        # Rate Limiting
        config.max_requests_per_minute = self._get_int(
            "MAX_REQUESTS_PER_MINUTE", config.max_requests_per_minute
        )
        config.max_requests_per_hour = self._get_int(
            "MAX_REQUESTS_PER_HOUR", config.max_requests_per_hour
        )
        config.max_requests_per_day = self._get_int(
            "MAX_REQUESTS_PER_DAY", config.max_requests_per_day
        )

        # Security Settings
        config.enable_security_filtering = self._get_bool(
            "ENABLE_SECURITY_FILTERING", config.enable_security_filtering
        )
        config.security_level = os.getenv("SECURITY_LEVEL", config.security_level)
        config.quarantine_enabled = self._get_bool(
            "QUARANTINE_ENABLED", config.quarantine_enabled
        )

        # Pipeline Settings
        config.input_folder = os.getenv("INPUT_FOLDER", config.input_folder)
        config.filtered_folder = os.getenv("FILTERED_FOLDER", config.filtered_folder)
        config.output_folder = os.getenv("OUTPUT_FOLDER", config.output_folder)
        config.error_folder = os.getenv("ERROR_FOLDER", config.error_folder)
        config.archive_folder = os.getenv("ARCHIVE_FOLDER", config.archive_folder)

        # Processing Settings
        config.output_format = os.getenv("OUTPUT_FORMAT", config.output_format)
        config.parallel_processing = self._get_bool(
            "PARALLEL_PROCESSING", config.parallel_processing
        )
        config.max_workers = self._get_int("MAX_WORKERS", config.max_workers)
        config.batch_size = self._get_int("BATCH_SIZE", config.batch_size)
        config.processing_interval = self._get_float(
            "PROCESSING_INTERVAL", config.processing_interval
        )
        config.auto_move_files = self._get_bool(
            "AUTO_MOVE_FILES", config.auto_move_files
        )

        # File Monitoring
        config.watch_input_folder = self._get_bool(
            "WATCH_INPUT_FOLDER", config.watch_input_folder
        )
        config.file_check_interval = self._get_float(
            "FILE_CHECK_INTERVAL", config.file_check_interval
        )
        config.max_file_size_mb = self._get_int(
            "MAX_FILE_SIZE_MB", config.max_file_size_mb
        )

        # Logging Settings
        config.log_level = os.getenv("LOG_LEVEL", config.log_level)
        config.log_to_file = self._get_bool("LOG_TO_FILE", config.log_to_file)
        config.log_file_max_size_mb = self._get_int(
            "LOG_FILE_MAX_SIZE_MB", config.log_file_max_size_mb
        )
        config.log_file_backup_count = self._get_int(
            "LOG_FILE_BACKUP_COUNT", config.log_file_backup_count
        )

        # Database Settings
        config.database_url = os.getenv("DATABASE_URL", config.database_url)
        config.enable_database_logging = self._get_bool(
            "ENABLE_DATABASE_LOGGING", config.enable_database_logging
        )

        # Notification Settings
        config.enable_notifications = self._get_bool(
            "ENABLE_NOTIFICATIONS", config.enable_notifications
        )
        config.notification_webhook_url = os.getenv("NOTIFICATION_WEBHOOK_URL")
        config.notification_email = os.getenv("NOTIFICATION_EMAIL")

        # Advanced AI Settings
        config.use_function_calling = self._get_bool(
            "USE_FUNCTION_CALLING", config.use_function_calling
        )
        config.enable_streaming = self._get_bool(
            "ENABLE_STREAMING", config.enable_streaming
        )
        config.custom_system_prompt = os.getenv("CUSTOM_SYSTEM_PROMPT")

        # Model Fallback Settings
        config.fallback_model = os.getenv("FALLBACK_MODEL", config.fallback_model)
        config.enable_model_fallback = self._get_bool(
            "ENABLE_MODEL_FALLBACK", config.enable_model_fallback
        )
        config.fallback_on_error = self._get_bool(
            "FALLBACK_ON_ERROR", config.fallback_on_error
        )
        config.fallback_on_cost_limit = self._get_bool(
            "FALLBACK_ON_COST_LIMIT", config.fallback_on_cost_limit
        )

        # Content Enhancement Settings
        config.auto_enhance_grammar = self._get_bool(
            "AUTO_ENHANCE_GRAMMAR", config.auto_enhance_grammar
        )
        config.auto_enhance_clarity = self._get_bool(
            "AUTO_ENHANCE_CLARITY", config.auto_enhance_clarity
        )
        config.auto_enhance_structure = self._get_bool(
            "AUTO_ENHANCE_STRUCTURE", config.auto_enhance_structure
        )
        config.preserve_original_meaning = self._get_bool(
            "PRESERVE_ORIGINAL_MEANING", config.preserve_original_meaning
        )
        config.enhancement_batch_size = self._get_int(
            "ENHANCEMENT_BATCH_SIZE", config.enhancement_batch_size
        )

        # Personality Modification Settings
        config.enable_personality_modifier = self._get_bool(
            "ENABLE_PERSONALITY_MODIFIER", config.enable_personality_modifier
        )
        config.personality_template = os.getenv(
            "PERSONALITY_TEMPLATE", config.personality_template
        )
        config.personality_strength = self._get_float(
            "PERSONALITY_STRENGTH", config.personality_strength
        )
        config.custom_personality_description = os.getenv(
            "CUSTOM_PERSONALITY_DESCRIPTION"
        )
        config.custom_personalities = self._get_json(
            "CUSTOM_PERSONALITIES", config.custom_personalities or {}
        )
        config.personality_preserve_meaning = self._get_bool(
            "PERSONALITY_PRESERVE_MEANING", config.personality_preserve_meaning
        )
        config.personality_min_confidence = self._get_float(
            "PERSONALITY_MIN_CONFIDENCE", config.personality_min_confidence
        )
        config.personality_cache_enabled = self._get_bool(
            "PERSONALITY_CACHE_ENABLED", config.personality_cache_enabled
        )
        config.personality_fallback_to_rules = self._get_bool(
            "PERSONALITY_FALLBACK_TO_RULES", config.personality_fallback_to_rules
        )

        return config

    def _get_bool(self, key: str, default: bool) -> bool:
        """Get boolean value from environment variable."""
        value = os.getenv(key)
        if value is None:
            return default

        return value.lower() in ("true", "1", "yes", "on", "enabled")

    def _get_int(self, key: str, default: int) -> int:
        """Get integer value from environment variable."""
        value = os.getenv(key)
        if value is None:
            return default

        try:
            return int(value)
        except ValueError:
            self.logger.warning(
                f"Invalid integer value for {key}: {value}. Using default: {default}"
            )
            return default

    def _get_float(self, key: str, default: float) -> float:
        """Get float value from environment variable."""
        value = os.getenv(key)
        if value is None:
            return default

        try:
            return float(value)
        except ValueError:
            self.logger.warning(
                f"Invalid float value for {key}: {value}. Using default: {default}"
            )
            return default

    def _get_list(
        self, key: str, default: List[str], separator: str = ","
    ) -> List[str]:
        """Get list value from environment variable."""
        value = os.getenv(key)
        if value is None:
            return default

        return [item.strip() for item in value.split(separator) if item.strip()]

    def _get_json(self, key: str, default: dict) -> dict:
        """Get JSON value from environment variable."""
        value = os.getenv(key)
        if value is None or not value.strip():
            return default

        try:
            import json

            return json.loads(value)
        except json.JSONDecodeError:
            self.logger.warning(
                f"Invalid JSON value for {key}: {value}. Using default."
            )
            return default

    def validate_config(self, config: EnvironmentConfig) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []

        # Check required settings
        valid_providers = ["openai", "openrouter", "lmstudio", "ollama"]
        if config.openai_provider not in valid_providers:
            issues.append(f"Invalid OPENAI_PROVIDER: {config.openai_provider}")

        if config.openai_provider == "openrouter":
            if not (config.openrouter_api_key or config.openai_api_key):
                issues.append(
                    "OPENROUTER_API_KEY is required when OPENAI_PROVIDER=openrouter"
                )
        elif config.openai_provider == "openai" and not config.openai_api_key:
            issues.append("OPENAI_API_KEY is required when OPENAI_PROVIDER=openai")

        # Validate model names
        valid_models = [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo-preview",
            "gpt-4o",
            "gpt-4o-mini",
        ]

        if (
            config.openai_provider == "openai"
            and config.openai_model not in valid_models
        ):
            issues.append(f"Invalid OpenAI model: {config.openai_model}")

        if (
            config.openai_provider == "openai"
            and config.fallback_model not in valid_models
        ):
            issues.append(f"Invalid fallback model: {config.fallback_model}")

        # Validate numeric ranges
        if config.daily_cost_limit <= 0:
            issues.append("DAILY_COST_LIMIT must be positive")

        if config.ai_confidence_threshold < 0 or config.ai_confidence_threshold > 1:
            issues.append("AI_CONFIDENCE_THRESHOLD must be between 0 and 1")

        if config.max_workers <= 0:
            issues.append("MAX_WORKERS must be positive")

        # Validate security level
        valid_security_levels = ["permissive", "balanced", "strict", "paranoid"]
        if config.security_level not in valid_security_levels:
            issues.append(f"Invalid security level: {config.security_level}")

        # Validate output format
        valid_formats = [
            "qwen",
            "alpaca",
            "chatml",
            "sharegpt",
            "llama2",
            "vicuna",
            "openai",
            "anthropic",
            "mistral",
            "gemma",
            "gpt_jsonl",
        ]
        if config.output_format not in valid_formats:
            issues.append(f"Invalid output format: {config.output_format}")

        return issues

    def create_template_env_file(self, file_path: str = ".env.template"):
        """Create a template .env file with all available configuration options."""
        sample_content = """# AI-Enhanced Text Processing Pipeline Configuration
# Copy this file to .env and customize the values

# ============================================================================
# OpenAI API Settings
# ============================================================================
# OPENAI_PROVIDER supports: openai | openrouter | lmstudio | ollama
OPENAI_PROVIDER=openai
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=1000
OPENAI_TIMEOUT=30

# OpenRouter (optional, if OPENAI_PROVIDER=openrouter)
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=
OPENROUTER_APP_NAME=AI Data Pipeline

# LM Studio / Ollama (OpenAI-compatible local providers; key not required)
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1

# ============================================================================
# Cost Control
# ============================================================================
DAILY_COST_LIMIT=20.0
COST_PER_REQUEST_LIMIT=0.10
ENABLE_COST_ALERTS=true

# ============================================================================
# AI Features
# ============================================================================
ENABLE_AI_CLASSIFICATION=true
ENABLE_CONTENT_ENHANCEMENT=true
ENABLE_SMART_SEGMENTATION=true
AI_CONFIDENCE_THRESHOLD=0.8
ENHANCEMENT_QUALITY_THRESHOLD=0.7

# ============================================================================
# Caching Settings
# ============================================================================
ENABLE_CACHING=true
CACHE_DURATION_HOURS=24
CACHE_CLEANUP_INTERVAL=168
MAX_CACHE_SIZE_MB=500

# ============================================================================
# Rate Limiting
# ============================================================================
MAX_REQUESTS_PER_MINUTE=60
MAX_REQUESTS_PER_HOUR=3000
MAX_REQUESTS_PER_DAY=10000

# ============================================================================
# Security Settings
# ============================================================================
ENABLE_SECURITY_FILTERING=true
SECURITY_LEVEL=balanced
QUARANTINE_ENABLED=true

# ============================================================================
# Pipeline Folders
# ============================================================================
INPUT_FOLDER=input
FILTERED_FOLDER=filtered
OUTPUT_FOLDER=output
ERROR_FOLDER=errors
ARCHIVE_FOLDER=archive

# ============================================================================
# Processing Settings
# ============================================================================
OUTPUT_FORMAT=qwen
PARALLEL_PROCESSING=true
MAX_WORKERS=4
BATCH_SIZE=10
PROCESSING_INTERVAL=5.0
AUTO_MOVE_FILES=true

# ============================================================================
# File Monitoring
# ============================================================================
WATCH_INPUT_FOLDER=true
FILE_CHECK_INTERVAL=2.0
MAX_FILE_SIZE_MB=100

# ============================================================================
# Logging Settings
# ============================================================================
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE_MAX_SIZE_MB=10
LOG_FILE_BACKUP_COUNT=5

# ============================================================================
# Database Settings
# ============================================================================
DATABASE_URL=sqlite:///pipeline.db
ENABLE_DATABASE_LOGGING=true

# ============================================================================
# Notification Settings
# ============================================================================
ENABLE_NOTIFICATIONS=false
NOTIFICATION_WEBHOOK_URL=
NOTIFICATION_EMAIL=

# ============================================================================
# Advanced AI Settings
# ============================================================================
USE_FUNCTION_CALLING=false
ENABLE_STREAMING=false
CUSTOM_SYSTEM_PROMPT=

# ============================================================================
# Model Fallback Settings
# ============================================================================
FALLBACK_MODEL=gpt-3.5-turbo
ENABLE_MODEL_FALLBACK=true
FALLBACK_ON_ERROR=true
FALLBACK_ON_COST_LIMIT=true

# ============================================================================
# Content Enhancement Settings
# ============================================================================
AUTO_ENHANCE_GRAMMAR=true
AUTO_ENHANCE_CLARITY=false
AUTO_ENHANCE_STRUCTURE=false
PRESERVE_ORIGINAL_MEANING=true
ENHANCEMENT_BATCH_SIZE=5
"""

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_content)

        self.logger.info(f"Created template environment file: {file_path}")


# Global configuration instance
_config_loader = None
_current_config = None


def get_config() -> EnvironmentConfig:
    """Get the current configuration, loading it if necessary."""
    global _config_loader, _current_config

    if _current_config is None:
        _config_loader = EnvironmentConfigLoader()
        _current_config = _config_loader.load_config()

    return _current_config


def reload_config() -> EnvironmentConfig:
    """Reload configuration from environment."""
    global _config_loader, _current_config

    _config_loader = EnvironmentConfigLoader()
    _current_config = _config_loader.load_config()

    return _current_config


def validate_current_config() -> List[str]:
    """Validate the current configuration."""
    global _config_loader

    if _config_loader is None:
        _config_loader = EnvironmentConfigLoader()

    config = get_config()
    return _config_loader.validate_config(config)
