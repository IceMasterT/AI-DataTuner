#!/usr/bin/env python3
"""
Personality Modifier System for adding custom voices and styles to training data.
Transforms text between filtered and output stages with AI-powered personality injection.
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging

from openai_integration import OpenAIClient, OpenAIConfig
from env_config import get_config


@dataclass
class PersonalityTemplate:
    """Represents a personality template."""

    name: str
    description: str
    system_prompt: str
    examples: List[Dict[str, str]]
    strength_modifier: float = 1.0
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class PersonalityResult:
    """Result of personality modification."""

    original_text: str
    modified_text: str
    personality_applied: str
    strength_used: float
    confidence: float
    cost: float
    tokens_used: int
    processing_time: float
    improvements: List[str]
    cached: bool = False


class PersonalityTemplateManager:
    """Manages personality templates and presets."""

    def __init__(self):
        self.templates: Dict[str, PersonalityTemplate] = {}
        self.logger = logging.getLogger(__name__)
        self._load_default_templates()
        self._load_custom_templates()

    def _load_default_templates(self):
        """Load default personality templates."""
        default_templates = {
            "neutral": PersonalityTemplate(
                name="neutral",
                description="Maintain neutral, balanced tone without adding personality",
                system_prompt="Maintain the original meaning and tone. Make minimal changes for clarity only.",
                examples=[
                    {
                        "input": "This is a technical explanation.",
                        "output": "This is a technical explanation.",
                    }
                ],
                tags=["default", "minimal"],
            ),
            "casual": PersonalityTemplate(
                name="casual",
                description="Casual, friendly language with modern expressions",
                system_prompt="Rewrite the text in a casual, friendly tone. Use modern expressions, contractions, and a relaxed conversational style. Keep it approachable and easy to understand.",
                examples=[
                    {
                        "input": "Machine learning is a complex field.",
                        "output": "Machine learning's pretty complex stuff, but it's really cool once you get into it!",
                    },
                    {
                        "input": "Please follow the instructions carefully.",
                        "output": "Just follow these steps and you'll be good to go!",
                    },
                ],
                tags=["friendly", "modern", "conversational"],
            ),
            "professional": PersonalityTemplate(
                name="professional",
                description="Professional but approachable business communication",
                system_prompt="Rewrite in a professional yet approachable tone. Use clear, business-appropriate language while remaining friendly and accessible.",
                examples=[
                    {
                        "input": "This might work.",
                        "output": "This approach should prove effective for our objectives.",
                    },
                    {
                        "input": "Let's try this.",
                        "output": "I recommend we implement this solution.",
                    },
                ],
                tags=["business", "formal", "clear"],
            ),
            "technical": PersonalityTemplate(
                name="technical",
                description="Precise technical language with detailed explanations",
                system_prompt="Rewrite using precise technical language. Add specific details, use proper terminology, and provide clear explanations with examples where helpful.",
                examples=[
                    {
                        "input": "The system works well.",
                        "output": "The system demonstrates optimal performance with 99.9% uptime and sub-millisecond response times.",
                    },
                    {
                        "input": "Save the file.",
                        "output": "Execute a write operation to persist the data structure to the designated storage location.",
                    },
                ],
                tags=["precise", "detailed", "technical"],
            ),
            "creative": PersonalityTemplate(
                name="creative",
                description="Imaginative language with metaphors and storytelling",
                system_prompt="Rewrite using creative, imaginative language. Use metaphors, analogies, and storytelling elements to make the content engaging and memorable.",
                examples=[
                    {
                        "input": "Data flows through the system.",
                        "output": "Data dances through the system like a river flowing through a digital landscape.",
                    },
                    {
                        "input": "The algorithm learns patterns.",
                        "output": "The algorithm becomes a detective, uncovering hidden patterns like clues in a mystery.",
                    },
                ],
                tags=["imaginative", "metaphorical", "engaging"],
            ),
            "friendly": PersonalityTemplate(
                name="friendly",
                description="Warm, encouraging, and supportive tone",
                system_prompt="Rewrite in a warm, encouraging tone. Be supportive, positive, and helpful. Use inclusive language and show enthusiasm.",
                examples=[
                    {
                        "input": "This is difficult.",
                        "output": "This can be challenging, but don't worry - you've got this! Let's break it down together.",
                    },
                    {
                        "input": "Follow these steps.",
                        "output": "Here are some helpful steps that'll guide you through this - I'm here to help!",
                    },
                ],
                tags=["supportive", "positive", "encouraging"],
            ),
            "humorous": PersonalityTemplate(
                name="humorous",
                description="Light-hearted with appropriate humor and wit",
                system_prompt="Add appropriate humor and wit while maintaining the core message. Use light-hearted comments, clever observations, and gentle humor to make content engaging.",
                examples=[
                    {
                        "input": "This process takes time.",
                        "output": "This process takes time - kind of like waiting for your coffee to brew, but hopefully more rewarding!",
                    },
                    {
                        "input": "Check your settings.",
                        "output": "Time to play detective with your settings - they're probably hiding something interesting!",
                    },
                ],
                tags=["witty", "entertaining", "light"],
            ),
            "educational": PersonalityTemplate(
                name="educational",
                description="Clear explanations with step-by-step guidance",
                system_prompt="Rewrite in an educational tone. Provide clear explanations, break down complex concepts, and offer step-by-step guidance. Be patient and thorough.",
                examples=[
                    {
                        "input": "Use this feature.",
                        "output": "Let's explore this feature step by step. First, you'll notice... This helps because... Next, you can...",
                    },
                    {
                        "input": "This is important.",
                        "output": "This concept is crucial to understand because it forms the foundation for everything that follows. Here's why...",
                    },
                ],
                tags=["instructional", "clear", "thorough"],
            ),
            "conversational": PersonalityTemplate(
                name="conversational",
                description="Natural dialogue-like language as if speaking with a friend",
                system_prompt="Rewrite as if you're having a natural conversation with a friend. Use dialogue-like language, ask rhetorical questions, and create a sense of back-and-forth discussion.",
                examples=[
                    {
                        "input": "This method is effective.",
                        "output": "You know what? This method really works well. Have you tried something like this before?",
                    },
                    {
                        "input": "Consider the options.",
                        "output": "So, what do you think? We've got a few options here, and honestly, each one has its perks.",
                    },
                ],
                tags=["natural", "dialogue", "interactive"],
            ),
        }

        self.templates.update(default_templates)
        self.logger.info(
            f"Loaded {len(default_templates)} default personality templates"
        )

    def _load_custom_templates(self):
        """Load custom personality templates from file."""
        custom_file = Path("personalities.json")

        if custom_file.exists():
            try:
                with open(custom_file, "r", encoding="utf-8") as f:
                    custom_data = json.load(f)

                for name, data in custom_data.items():
                    template = PersonalityTemplate(
                        name=name,
                        description=data.get("description", ""),
                        system_prompt=data.get(
                            "system_prompt", data.get("description", "")
                        ),
                        examples=data.get("examples", []),
                        strength_modifier=data.get("strength_modifier", 1.0),
                        tags=data.get("tags", ["custom"]),
                    )
                    self.templates[name] = template

                self.logger.info(
                    f"Loaded {len(custom_data)} custom personality templates"
                )

            except Exception as e:
                self.logger.error(f"Error loading custom templates: {e}")

    def get_template(self, name: str) -> Optional[PersonalityTemplate]:
        """Get a personality template by name."""
        return self.templates.get(name)

    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(self.templates.keys())

    def get_templates_by_tag(self, tag: str) -> List[PersonalityTemplate]:
        """Get templates that have a specific tag."""
        return [
            template for template in self.templates.values() if tag in template.tags
        ]

    def save_custom_template(self, template: PersonalityTemplate) -> bool:
        """Save a custom personality template."""
        try:
            custom_file = Path("personalities.json")
            custom_data = {}

            if custom_file.exists():
                with open(custom_file, "r", encoding="utf-8") as f:
                    custom_data = json.load(f)

            custom_data[template.name] = {
                "description": template.description,
                "system_prompt": template.system_prompt,
                "examples": template.examples,
                "strength_modifier": template.strength_modifier,
                "tags": template.tags,
                "created": datetime.now().isoformat(),
            }

            with open(custom_file, "w", encoding="utf-8") as f:
                json.dump(custom_data, f, indent=2)

            # Add to current templates
            self.templates[template.name] = template

            self.logger.info(f"Saved custom template: {template.name}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving custom template: {e}")
            return False


class PersonalityModifier:
    """Main personality modification system."""

    def __init__(self, openai_config: Optional[OpenAIConfig] = None):
        self.template_manager = PersonalityTemplateManager()
        self.logger = logging.getLogger(__name__)

        # Initialize custom personality manager
        from custom_personality_manager import get_custom_personality_manager

        self.custom_manager = get_custom_personality_manager()

        # Initialize OpenAI client if available
        if openai_config:
            self.ai_client = OpenAIClient(openai_config)
        else:
            config = get_config()
            if config.openai_api_key:
                provider = getattr(config, "openai_provider", "openai")
                provider_base_url = None
                if provider == "openrouter":
                    provider_base_url = getattr(config, "openrouter_base_url", None)
                elif provider == "lmstudio":
                    provider_base_url = getattr(config, "lmstudio_base_url", None)
                elif provider == "ollama":
                    provider_base_url = getattr(config, "ollama_base_url", None)

                ai_config = OpenAIConfig(
                    provider=provider,
                    api_key=config.openai_api_key,
                    model=config.openai_model,
                    base_url=provider_base_url,
                    app_name=getattr(config, "openrouter_app_name", "AI Data Pipeline"),
                    app_url=getattr(config, "openrouter_site_url", None),
                    cost_limit_per_day=config.daily_cost_limit,
                )
                self.ai_client = OpenAIClient(ai_config)
            else:
                self.ai_client = None
                self.logger.warning(
                    "No OpenAI configuration available - personality modification will use rule-based fallbacks"
                )

    def apply_personality(
        self, text: str, personality: str, strength: float = 0.7
    ) -> PersonalityResult:
        """
        Apply personality modification to text.

        Args:
            text: Original text to modify
            personality: Personality template name or custom description
            strength: Strength of personality application (0.0 to 1.0)

        Returns:
            PersonalityResult with modified text and metadata
        """
        import time

        start_time = time.time()

        result = PersonalityResult(
            original_text=text,
            modified_text=text,
            personality_applied=personality,
            strength_used=strength,
            confidence=0.0,
            cost=0.0,
            tokens_used=0,
            processing_time=0.0,
            improvements=[],
        )

        try:
            # Check for custom personalities first
            custom_description = self.custom_manager.get_personality_for_processing(
                personality
            )

            if custom_description:
                # Use custom personality
                system_prompt = self._build_custom_prompt(custom_description, strength)
                result.improvements.append(f"Applied custom personality: {personality}")
            else:
                # Get predefined template
                template = self.template_manager.get_template(personality)

                if template:
                    # Use predefined template
                    system_prompt = self._build_system_prompt(template, strength)
                    result.improvements.append(
                        f"Applied {template.name} personality template"
                    )
                else:
                    # Use as direct personality description
                    system_prompt = self._build_custom_prompt(personality, strength)
                    result.improvements.append("Applied direct personality description")

            # Apply personality modification
            if self.ai_client:
                # Use AI for personality modification
                ai_result = self._apply_ai_personality(text, system_prompt)

                result.modified_text = ai_result["response"]
                result.confidence = ai_result.get("confidence", 0.8)
                result.cost = ai_result["cost"]
                result.tokens_used = ai_result["tokens_used"]
                result.cached = ai_result.get("cached", False)

                if result.cached:
                    result.improvements.append("Used cached response")

            else:
                # Use rule-based fallback
                result.modified_text = self._apply_rule_based_personality(
                    text, personality, strength
                )
                result.confidence = 0.6  # Lower confidence for rule-based
                result.improvements.append("Used rule-based personality modification")

            result.processing_time = time.time() - start_time

            self.logger.info(
                f"Applied personality '{personality}' with strength {strength:.1f}"
            )

        except Exception as e:
            self.logger.error(f"Error applying personality: {e}")
            result.improvements.append(f"Error: {str(e)}")

        return result

    def _build_system_prompt(
        self, template: PersonalityTemplate, strength: float
    ) -> str:
        """Build system prompt from template."""
        base_prompt = template.system_prompt

        # Adjust strength
        if strength < 0.3:
            strength_instruction = (
                "Apply the personality very subtly, making minimal changes."
            )
        elif strength < 0.7:
            strength_instruction = "Apply the personality moderately, balancing original tone with new style."
        else:
            strength_instruction = "Apply the personality strongly, fully transforming the style while preserving meaning."

        # Add examples if available
        examples_text = ""
        if template.examples:
            examples_text = "\n\nExamples:\n"
            for example in template.examples[:3]:  # Limit to 3 examples
                examples_text += (
                    f"Input: {example['input']}\nOutput: {example['output']}\n\n"
                )

        return f"{base_prompt}\n\n{strength_instruction}{examples_text}"

    def _build_custom_prompt(self, personality_desc: str, strength: float) -> str:
        """Build system prompt from custom personality description."""
        strength_instruction = {
            0.1: "very subtly",
            0.3: "subtly",
            0.5: "moderately",
            0.7: "strongly",
            0.9: "very strongly",
        }

        # Find closest strength level
        strength_level = min(
            strength_instruction.keys(), key=lambda x: abs(x - strength)
        )
        strength_text = strength_instruction[strength_level]

        return f"""Rewrite the following text to match this personality and style: {personality_desc}

Apply this personality {strength_text}, ensuring you:
1. Preserve the original meaning and key information
2. Transform the tone and style according to the personality description
3. Keep the content appropriate and professional
4. Maintain clarity and readability

Transform the style while keeping the core message intact."""

    def _apply_ai_personality(self, text: str, system_prompt: str) -> Dict[str, Any]:
        """Apply personality using AI."""
        try:
            return self.ai_client.make_request(text, system_prompt)
        except Exception as e:
            self.logger.error(f"AI personality modification failed: {e}")
            raise

    def _apply_rule_based_personality(
        self, text: str, personality: str, strength: float
    ) -> str:
        """Apply personality using rule-based methods (fallback)."""
        # Simple rule-based personality modifications
        modified_text = text

        if "casual" in personality.lower():
            # Make more casual
            modified_text = re.sub(
                r"\bdo not\b", "don't", modified_text, flags=re.IGNORECASE
            )
            modified_text = re.sub(
                r"\bcannot\b", "can't", modified_text, flags=re.IGNORECASE
            )
            modified_text = re.sub(
                r"\bwill not\b", "won't", modified_text, flags=re.IGNORECASE
            )

            if strength > 0.5:
                modified_text = re.sub(r"\bHello\b", "Hey", modified_text)
                modified_text = re.sub(r"\bThank you\b", "Thanks", modified_text)

        elif "formal" in personality.lower() or "professional" in personality.lower():
            # Make more formal
            modified_text = re.sub(
                r"\bdon't\b", "do not", modified_text, flags=re.IGNORECASE
            )
            modified_text = re.sub(
                r"\bcan't\b", "cannot", modified_text, flags=re.IGNORECASE
            )
            modified_text = re.sub(
                r"\bwon't\b", "will not", modified_text, flags=re.IGNORECASE
            )

            if strength > 0.5:
                modified_text = re.sub(r"\bHey\b", "Hello", modified_text)
                modified_text = re.sub(r"\bThanks\b", "Thank you", modified_text)

        elif "friendly" in personality.lower():
            # Add friendly elements
            if strength > 0.5:
                if not modified_text.endswith(("!", "?", ".")):
                    modified_text += "!"

                # Add encouraging words
                modified_text = re.sub(r"\bThis is\b", "This is really", modified_text)
                modified_text = re.sub(
                    r"\bYou can\b", "You can definitely", modified_text
                )

        return modified_text

    def batch_apply_personality(
        self, texts: List[str], personality: str, strength: float = 0.7
    ) -> List[PersonalityResult]:
        """Apply personality to multiple texts efficiently."""
        results = []

        for text in texts:
            result = self.apply_personality(text, personality, strength)
            results.append(result)

        return results

    def get_available_personalities(self) -> Dict[str, str]:
        """Get all available personalities with descriptions."""
        personalities = {}

        # Add predefined templates
        for name, template in self.template_manager.templates.items():
            personalities[name] = template.description

        # Add custom personalities
        for (
            name,
            custom_personality,
        ) in self.custom_manager.custom_personalities.items():
            personalities[f"custom:{name}"] = custom_personality.description

        return personalities

    def preview_personality(
        self, sample_text: str, personality: str, strength: float = 0.7
    ) -> PersonalityResult:
        """Preview personality modification on sample text."""
        return self.apply_personality(sample_text, personality, strength)

    def create_custom_personality(
        self, name: str, description: str, examples: List[Dict[str, str]] = None
    ) -> bool:
        """Create and save a custom personality template."""
        if examples is None:
            examples = []

        template = PersonalityTemplate(
            name=name,
            description=description,
            system_prompt=description,
            examples=examples,
            tags=["custom"],
        )

        return self.template_manager.save_custom_template(template)
