#!/usr/bin/env python3
"""
Configuration management for AI-enhanced features.
Handles OpenAI API settings, cost controls, and feature toggles.
"""

import os
import json
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum


class AIModel(Enum):
    """Supported AI models."""

    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"


class ProcessingMode(Enum):
    """Processing modes for different use cases."""

    COST_OPTIMIZED = "cost_optimized"
    BALANCED = "balanced"
    QUALITY_OPTIMIZED = "quality_optimized"
    SPEED_OPTIMIZED = "speed_optimized"


@dataclass
class AIFeatureConfig:
    """Configuration for AI features."""

    # Core AI settings
    enable_ai_classification: bool = True
    enable_content_enhancement: bool = False
    enable_smart_segmentation: bool = True

    # Model selection
    classification_model: str = "gpt-3.5-turbo"
    enhancement_model: str = "gpt-3.5-turbo"

    # Quality thresholds
    ai_confidence_threshold: float = 0.8
    enhancement_quality_threshold: float = 0.7

    # Cost controls
    daily_cost_limit: float = 10.0
    cost_per_request_limit: float = 0.10
    enable_cost_alerts: bool = True

    # Performance settings
    enable_caching: bool = True
    cache_duration_hours: int = 24
    max_requests_per_minute: int = 60
    request_timeout_seconds: int = 30

    # Enhancement settings
    auto_enhance_grammar: bool = True
    auto_enhance_clarity: bool = False
    auto_enhance_structure: bool = False
    preserve_original_meaning: bool = True

    # Fallback settings
    fallback_to_rules_on_error: bool = True
    fallback_to_rules_on_cost_limit: bool = True


@dataclass
class ModelCapabilities:
    """Capabilities and costs for different models."""

    name: str
    max_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    supports_function_calling: bool
    context_window: int
    recommended_for: List[str]


class AIConfigManager:
    """Manages AI configuration and model selection."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        # Model capabilities database
        self.model_capabilities = self._init_model_capabilities()

        # Default configurations for different modes
        self.mode_configs = self._init_mode_configs()

        # Current configuration
        self.current_config = self.mode_configs[ProcessingMode.BALANCED]

    def _init_model_capabilities(self) -> Dict[str, ModelCapabilities]:
        """Initialize model capabilities database."""
        return {
            "gpt-3.5-turbo": ModelCapabilities(
                name="gpt-3.5-turbo",
                max_tokens=4096,
                cost_per_1k_input=0.0015,
                cost_per_1k_output=0.002,
                supports_function_calling=True,
                context_window=16385,
                recommended_for=[
                    "classification",
                    "basic_enhancement",
                    "cost_optimization",
                ],
            ),
            "gpt-4": ModelCapabilities(
                name="gpt-4",
                max_tokens=8192,
                cost_per_1k_input=0.03,
                cost_per_1k_output=0.06,
                supports_function_calling=True,
                context_window=8192,
                recommended_for=[
                    "complex_enhancement",
                    "high_accuracy",
                    "technical_content",
                ],
            ),
            "gpt-4-turbo-preview": ModelCapabilities(
                name="gpt-4-turbo-preview",
                max_tokens=4096,
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.03,
                supports_function_calling=True,
                context_window=128000,
                recommended_for=[
                    "long_content",
                    "complex_analysis",
                    "balanced_performance",
                ],
            ),
            "gpt-4o": ModelCapabilities(
                name="gpt-4o",
                max_tokens=4096,
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
                supports_function_calling=True,
                context_window=128000,
                recommended_for=[
                    "general_purpose",
                    "balanced_cost_quality",
                    "production",
                ],
            ),
            "gpt-4o-mini": ModelCapabilities(
                name="gpt-4o-mini",
                max_tokens=16384,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                supports_function_calling=True,
                context_window=128000,
                recommended_for=["high_volume", "cost_sensitive", "simple_tasks"],
            ),
        }

    def _init_mode_configs(self) -> Dict[ProcessingMode, AIFeatureConfig]:
        """Initialize predefined configuration modes."""
        configs = {}

        # Cost-optimized mode
        configs[ProcessingMode.COST_OPTIMIZED] = AIFeatureConfig(
            enable_ai_classification=True,
            enable_content_enhancement=False,
            enable_smart_segmentation=False,
            classification_model="gpt-4o-mini",
            enhancement_model="gpt-4o-mini",
            ai_confidence_threshold=0.9,
            enhancement_quality_threshold=0.9,
            daily_cost_limit=2.0,
            cost_per_request_limit=0.01,
            enable_caching=True,
            cache_duration_hours=48,
            auto_enhance_grammar=False,
            auto_enhance_clarity=False,
            auto_enhance_structure=False,
        )

        # Balanced mode (default)
        configs[ProcessingMode.BALANCED] = AIFeatureConfig(
            enable_ai_classification=True,
            enable_content_enhancement=True,
            enable_smart_segmentation=True,
            classification_model="gpt-4o",
            enhancement_model="gpt-4o",
            ai_confidence_threshold=0.8,
            enhancement_quality_threshold=0.7,
            daily_cost_limit=10.0,
            cost_per_request_limit=0.05,
            enable_caching=True,
            cache_duration_hours=24,
            auto_enhance_grammar=True,
            auto_enhance_clarity=False,
            auto_enhance_structure=False,
        )

        # Quality-optimized mode
        configs[ProcessingMode.QUALITY_OPTIMIZED] = AIFeatureConfig(
            enable_ai_classification=True,
            enable_content_enhancement=True,
            enable_smart_segmentation=True,
            classification_model="gpt-4-turbo-preview",
            enhancement_model="gpt-4-turbo-preview",
            ai_confidence_threshold=0.6,
            enhancement_quality_threshold=0.6,
            daily_cost_limit=25.0,
            cost_per_request_limit=0.20,
            enable_caching=True,
            cache_duration_hours=12,
            auto_enhance_grammar=True,
            auto_enhance_clarity=True,
            auto_enhance_structure=True,
        )

        # Speed-optimized mode
        configs[ProcessingMode.SPEED_OPTIMIZED] = AIFeatureConfig(
            enable_ai_classification=False,
            enable_content_enhancement=False,
            enable_smart_segmentation=False,
            classification_model="gpt-3.5-turbo",
            enhancement_model="gpt-3.5-turbo",
            ai_confidence_threshold=0.9,
            enhancement_quality_threshold=0.9,
            daily_cost_limit=1.0,
            cost_per_request_limit=0.005,
            enable_caching=True,
            cache_duration_hours=72,
            fallback_to_rules_on_error=True,
            fallback_to_rules_on_cost_limit=True,
        )

        return configs

    def load_mode(self, mode: ProcessingMode):
        """Load a predefined processing mode."""
        if mode in self.mode_configs:
            self.current_config = self.mode_configs[mode]
        else:
            raise ValueError(f"Unknown processing mode: {mode}")

    def load_config_from_file(self, config_file: str) -> bool:
        """Load configuration from file."""
        config_path = Path(config_file)

        if not config_path.exists():
            return False

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yaml", ".yml"]:
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)

            # Load AI feature config
            if "ai_features" in config_data:
                self.current_config = AIFeatureConfig(**config_data["ai_features"])

            return True
        except Exception as e:
            print(f"Error loading AI config: {e}")
            return False

    def save_config_to_file(self, config_file: str, format: str = "yaml") -> bool:
        """Save current configuration to file."""
        config_path = Path(config_file)

        try:
            config_data = {
                "ai_features": asdict(self.current_config),
                "model_capabilities": {
                    name: asdict(caps) for name, caps in self.model_capabilities.items()
                },
            }

            with open(config_path, "w", encoding="utf-8") as f:
                if format.lower() in ["yaml", "yml"]:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving AI config: {e}")
            return False

    def get_recommended_model(self, task_type: str, cost_priority: bool = False) -> str:
        """Get recommended model for a specific task."""
        suitable_models = []

        for model_name, capabilities in self.model_capabilities.items():
            if task_type in capabilities.recommended_for:
                suitable_models.append((model_name, capabilities))

        if not suitable_models:
            # Fallback to general purpose models
            suitable_models = [
                (name, caps) for name, caps in self.model_capabilities.items()
            ]

        if cost_priority:
            # Sort by cost (input + output cost)
            suitable_models.sort(
                key=lambda x: x[1].cost_per_1k_input + x[1].cost_per_1k_output
            )
        else:
            # Sort by capability (context window as proxy for capability)
            suitable_models.sort(key=lambda x: x[1].context_window, reverse=True)

        return suitable_models[0][0]

    def estimate_daily_cost(
        self, texts_per_day: int, avg_text_length: int
    ) -> Dict[str, float]:
        """Estimate daily costs for current configuration."""
        from openai_integration import TokenCounter

        # Estimate tokens per text
        tokens_per_text = TokenCounter.estimate_tokens(avg_text_length)

        # Get model costs
        classification_model = self.model_capabilities.get(
            self.current_config.classification_model
        )
        enhancement_model = self.model_capabilities.get(
            self.current_config.enhancement_model
        )

        costs = {}

        # Classification costs
        if self.current_config.enable_ai_classification and classification_model:
            input_tokens = tokens_per_text
            output_tokens = tokens_per_text // 10  # Assume small classification output

            classification_cost_per_text = (
                input_tokens / 1000
            ) * classification_model.cost_per_1k_input + (
                output_tokens / 1000
            ) * classification_model.cost_per_1k_output
            costs["classification"] = classification_cost_per_text * texts_per_day
        else:
            costs["classification"] = 0.0

        # Enhancement costs
        if self.current_config.enable_content_enhancement and enhancement_model:
            # Assume 30% of texts need enhancement
            enhancement_ratio = 0.3
            input_tokens = tokens_per_text
            output_tokens = tokens_per_text  # Assume similar length output

            enhancement_cost_per_text = (
                input_tokens / 1000
            ) * enhancement_model.cost_per_1k_input + (
                output_tokens / 1000
            ) * enhancement_model.cost_per_1k_output
            costs["enhancement"] = (
                enhancement_cost_per_text * texts_per_day * enhancement_ratio
            )
        else:
            costs["enhancement"] = 0.0

        costs["total"] = costs["classification"] + costs["enhancement"]
        costs["within_limit"] = costs["total"] <= self.current_config.daily_cost_limit

        return costs

    def validate_api_key(self, api_key: str = None) -> bool:
        """Validate OpenAI API key."""
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            return False

        try:
            # Try to make a minimal API call to validate
            import openai

            if hasattr(openai, "OpenAI"):
                client = openai.OpenAI(api_key=api_key)
                client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                )
            else:
                openai.api_key = api_key
                openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                )
            return True
        except Exception:
            return False

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration."""
        config_dict = asdict(self.current_config)

        # Add cost estimates
        daily_cost_estimate = self.estimate_daily_cost(
            100, 500
        )  # 100 texts, 500 chars each

        # Add model information
        classification_model_info = self.model_capabilities.get(
            self.current_config.classification_model
        )
        enhancement_model_info = self.model_capabilities.get(
            self.current_config.enhancement_model
        )

        summary = {
            "configuration": config_dict,
            "cost_estimates": daily_cost_estimate,
            "models": {
                "classification": asdict(classification_model_info)
                if classification_model_info
                else None,
                "enhancement": asdict(enhancement_model_info)
                if enhancement_model_info
                else None,
            },
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        }

        return summary

    def optimize_for_budget(self, daily_budget: float):
        """Optimize configuration for a specific daily budget."""
        self.current_config.daily_cost_limit = daily_budget

        if daily_budget < 1.0:
            # Very low budget - minimal AI usage
            self.current_config.enable_content_enhancement = False
            self.current_config.classification_model = "gpt-4o-mini"
            self.current_config.ai_confidence_threshold = 0.95
            self.current_config.cache_duration_hours = 72
        elif daily_budget < 5.0:
            # Low budget - basic AI features
            self.current_config.enable_content_enhancement = False
            self.current_config.classification_model = "gpt-4o-mini"
            self.current_config.ai_confidence_threshold = 0.9
        elif daily_budget < 15.0:
            # Medium budget - balanced features
            self.current_config.enable_content_enhancement = True
            self.current_config.classification_model = "gpt-4o"
            self.current_config.enhancement_model = "gpt-4o"
            self.current_config.auto_enhance_clarity = False
        else:
            # High budget - full features
            self.current_config.enable_content_enhancement = True
            self.current_config.classification_model = "gpt-4-turbo-preview"
            self.current_config.enhancement_model = "gpt-4-turbo-preview"
            self.current_config.auto_enhance_clarity = True
            self.current_config.auto_enhance_structure = True

    def create_custom_profile(
        self, profile_name: str, base_mode: ProcessingMode = ProcessingMode.BALANCED
    ) -> bool:
        """Create a custom configuration profile."""
        try:
            profile_path = self.config_dir / f"ai_profile_{profile_name}.yaml"

            # Start with base configuration
            base_config = self.mode_configs[base_mode]

            config_data = {
                "profile_name": profile_name,
                "base_mode": base_mode.value,
                "ai_features": asdict(base_config),
            }

            with open(profile_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)

            return True
        except Exception as e:
            print(f"Error creating custom profile: {e}")
            return False

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available models with their capabilities."""
        models = []
        for name, capabilities in self.model_capabilities.items():
            model_info = asdict(capabilities)
            model_info["cost_per_1k_total"] = (
                capabilities.cost_per_1k_input + capabilities.cost_per_1k_output
            )
            models.append(model_info)

        # Sort by cost
        models.sort(key=lambda x: x["cost_per_1k_total"])
        return models
