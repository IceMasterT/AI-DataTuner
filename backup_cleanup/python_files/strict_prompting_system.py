#!/usr/bin/env python3
"""
Strict Prompting System - Enhanced prompting for 95%+ accuracy in data formatting.
Implements multi-stage prompting, validation, and correction loops.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from openai_integration import OpenAIClient, OpenAIConfig
from env_config import get_config


@dataclass
class PromptingResult:
    """Result from strict prompting system."""

    formatted_content: str
    accuracy_score: float
    validation_passed: bool
    attempts_used: int
    corrections_applied: List[str]
    cost: float
    processing_time: float


class StrictPromptingSystem:
    """Enhanced prompting system with strict validation and correction loops."""

    def __init__(self, max_attempts: int = 3, target_accuracy: float = 95.0):
        """Initialize the strict prompting system."""
        self.max_attempts = max_attempts
        self.target_accuracy = target_accuracy
        self.logger = logging.getLogger(__name__)

        # Initialize OpenAI client
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
            raise ValueError("OpenAI API key required for strict prompting system")

    def format_with_strict_prompting(
        self,
        content: str,
        format_type: str,
        personality: str = "professional",
        context: str = None,
    ) -> PromptingResult:
        """
        Format content using strict prompting with validation loops.

        Args:
            content: Original content to format
            format_type: Target format (qwen, alpaca, chatml, etc.)
            personality: Personality to apply
            context: Additional context for formatting

        Returns:
            PromptingResult with formatted content and metrics
        """
        start_time = datetime.now()
        total_cost = 0.0
        corrections_applied = []

        # Build the strict formatting prompt
        base_prompt = self._build_strict_formatting_prompt(
            content, format_type, personality, context
        )

        best_result = None
        best_accuracy = 0.0

        for attempt in range(1, self.max_attempts + 1):
            self.logger.info(f"Formatting attempt {attempt}/{self.max_attempts}")

            # Apply progressive prompting strategy
            if attempt == 1:
                prompt = base_prompt
                system_message = self._get_base_system_message(format_type)
            elif attempt == 2:
                prompt = self._build_correction_prompt(base_prompt, best_result)
                system_message = self._get_strict_system_message(format_type)
            else:
                prompt = self._build_final_attempt_prompt(base_prompt, best_result)
                system_message = self._get_critical_system_message(format_type)

            try:
                # Make API request
                result = self.ai_client.make_request(prompt, system_message)
                formatted_content = result["response"].strip()
                total_cost += result.get("cost", 0.0)

                # Validate the result
                validation_result = self._validate_formatted_content(
                    formatted_content, format_type, content
                )

                accuracy = validation_result["accuracy_score"]

                # Track best result
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_result = {
                        "content": formatted_content,
                        "validation": validation_result,
                        "attempt": attempt,
                    }

                # Check if we've met the target
                if accuracy >= self.target_accuracy and validation_result["is_valid"]:
                    corrections_applied.append(
                        f"Achieved target accuracy on attempt {attempt}"
                    )
                    break

                # Apply corrections for next attempt
                if attempt < self.max_attempts:
                    correction_info = self._analyze_and_correct(
                        formatted_content, validation_result, format_type
                    )
                    corrections_applied.extend(correction_info["corrections"])

            except Exception as e:
                self.logger.error(f"Formatting attempt {attempt} failed: {e}")
                corrections_applied.append(f"Attempt {attempt} failed: {e}")
                continue

        # Use best result if no perfect result achieved
        if best_result is None:
            raise RuntimeError("All formatting attempts failed")

        processing_time = (datetime.now() - start_time).total_seconds()

        return PromptingResult(
            formatted_content=best_result["content"],
            accuracy_score=best_accuracy,
            validation_passed=best_result["validation"]["is_valid"],
            attempts_used=best_result["attempt"],
            corrections_applied=corrections_applied,
            cost=total_cost,
            processing_time=processing_time,
        )

    def _build_strict_formatting_prompt(
        self, content: str, format_type: str, personality: str, context: str = None
    ) -> str:
        """Build a strict formatting prompt with detailed requirements."""

        format_specs = self._get_format_specifications(format_type)
        personality_specs = self._get_personality_specifications(personality)

        prompt = f"""
CRITICAL DATA FORMATTING TASK - 95% ACCURACY REQUIRED

ORIGINAL CONTENT TO FORMAT:
{content}

TARGET FORMAT: {format_type.upper()}
{format_specs}

PERSONALITY REQUIREMENTS: {personality.upper()}
{personality_specs}

STRICT FORMATTING RULES:
1. PRESERVE 100% of factual information from original content
2. DO NOT add information not present in original
3. DO NOT change or omit factual claims
4. MAINTAIN exact format specifications for {format_type}
5. Apply {personality} personality consistently throughout
6. Ensure natural, fluent conversation flow
7. Validate format compliance before responding

QUALITY REQUIREMENTS:
- Factual Accuracy: 100% (no changes to facts)
- Format Compliance: 100% (exact format match)
- Completeness: 100% (all information preserved)
- Consistency: 100% (uniform style and tone)
- Fluency: Natural conversation flow

VALIDATION CHECKLIST:
□ All original facts preserved exactly
□ Format matches {format_type} specification perfectly
□ {personality} personality applied consistently
□ No grammatical or formatting errors
□ Complete conversation structure
□ Natural flow and readability

{context or ""}

RESPOND WITH ONLY THE PERFECTLY FORMATTED CONTENT. NO EXPLANATIONS OR COMMENTS.
"""

        return prompt.strip()

    def _get_format_specifications(self, format_type: str) -> str:
        """Get detailed format specifications."""
        specs = {
            "qwen": """
QWEN FORMAT SPECIFICATION:
- Structure: <|user|>\\n[user_content]\\n<|assistant|>\\n[assistant_content]
- Delimiters: Exactly <|user|> and <|assistant|> (no spaces inside)
- Spacing: Single newline after each delimiter
- Multiple turns: Separate with double newline
- No extra formatting, decorations, or markdown
- Example:
  <|user|>
  What is machine learning?
  <|assistant|>
  Machine learning is a method of data analysis...
            """,
            "alpaca": """
ALPACA FORMAT SPECIFICATION:
- Structure: ### Instruction:\\n[instruction]\\n\\n### Response:\\n[response]
- Headers: Exactly three # symbols, single space after colon
- Spacing: Double newline between instruction and response
- No additional formatting or decorations
- Example:
  ### Instruction:
  Explain machine learning concepts.
  
  ### Response:
  Machine learning is a method of data analysis...
            """,
            "chatml": """
CHATML FORMAT SPECIFICATION:
- Structure: <|im_start|>user\\n[content]\\n<|im_end|>\\n<|im_start|>assistant\\n[content]\\n<|im_end|>
- Delimiters: Exactly <|im_start|> and <|im_end|> (no spaces)
- Roles: user, assistant, system only
- Each message must be properly closed
- Example:
  <|im_start|>user
  What is machine learning?
  <|im_end|>
  <|im_start|>assistant
  Machine learning is a method of data analysis...
  <|im_end|>
            """,
            "sharegpt": """
SHAREGPT JSON FORMAT SPECIFICATION:
- Structure: JSON array with conversation objects
- Required fields: "from" (human/gpt), "value" (content)
- Proper JSON escaping for special characters
- Example:
  [
    {"from": "human", "value": "What is machine learning?"},
    {"from": "gpt", "value": "Machine learning is a method..."}
  ]
            """,
            "llama2": """
LLAMA-2 FORMAT SPECIFICATION:
- Structure: [INST] [instruction] [/INST] [response]
- Delimiters: Exactly [INST] and [/INST] with spaces
- Single space after opening delimiter
- No additional formatting
- Example:
  [INST] What is machine learning? [/INST] Machine learning is a method...
            """,
        }

        return specs.get(format_type, f"Unknown format: {format_type}")

    def _get_personality_specifications(self, personality: str) -> str:
        """Get detailed personality specifications."""
        specs = {
            "professional": """
PROFESSIONAL PERSONALITY:
- Formal, business-appropriate tone
- Clear, concise explanations
- Avoid casual language or slang
- Use complete sentences and proper grammar
- Maintain respectful, authoritative voice
- Focus on accuracy and clarity
            """,
            "casual": """
CASUAL PERSONALITY:
- Relaxed, conversational tone
- Use contractions (don't, can't, it's)
- Friendly and approachable language
- Natural speech patterns
- Avoid overly formal language
- Maintain warmth and accessibility
            """,
            "technical": """
TECHNICAL PERSONALITY:
- Precise, detailed explanations
- Use appropriate technical terminology
- Focus on accuracy and specificity
- Include relevant technical details
- Maintain analytical approach
- Avoid oversimplification
            """,
            "educational": """
EDUCATIONAL PERSONALITY:
- Clear, instructional tone
- Break down complex concepts
- Use examples and analogies
- Progressive explanation structure
- Encourage understanding
- Patient and thorough approach
            """,
            "friendly": """
FRIENDLY PERSONALITY:
- Warm, welcoming tone
- Use encouraging language
- Show enthusiasm for helping
- Personal and engaging style
- Positive and supportive approach
- Maintain approachability
            """,
        }

        return specs.get(personality, f"Apply {personality} personality consistently")

    def _get_base_system_message(self, format_type: str) -> str:
        """Get base system message for first attempt."""
        return f"""You are an expert data formatter specializing in {format_type} format. Your task is to transform content while maintaining 100% factual accuracy and perfect format compliance. Focus on precision, clarity, and exact format adherence."""

    def _get_strict_system_message(self, format_type: str) -> str:
        """Get strict system message for correction attempts."""
        return f"""You are a strict data formatting validator. The previous attempt did not meet the 95% accuracy requirement. You must now apply maximum precision to achieve perfect {format_type} formatting while preserving every factual detail from the original content. No errors are acceptable."""

    def _get_critical_system_message(self, format_type: str) -> str:
        """Get critical system message for final attempts."""
        return f"""CRITICAL FINAL ATTEMPT: You are the last line of defense for data accuracy. The content MUST achieve 95%+ accuracy with perfect {format_type} formatting. Every word, every delimiter, every structure element must be exactly correct. Failure is not an option. Apply maximum attention to detail and validation."""

    def _build_correction_prompt(self, base_prompt: str, best_result: dict) -> str:
        """Build correction prompt based on previous attempt."""
        if not best_result:
            return base_prompt

        validation = best_result.get("validation", {})
        errors = validation.get("errors", [])
        accuracy = validation.get("accuracy_score", 0)

        correction_prompt = f"""
CORRECTION ATTEMPT - Previous accuracy: {accuracy:.1f}%

PREVIOUS ERRORS TO FIX:
{chr(10).join(f"• {error}" for error in errors[:5])}

{base_prompt}

CRITICAL CORRECTIONS NEEDED:
- Fix all identified errors from previous attempt
- Ensure 95%+ accuracy is achieved
- Perfect format compliance required
- No factual changes to original content
"""

        return correction_prompt

    def _build_final_attempt_prompt(self, base_prompt: str, best_result: dict) -> str:
        """Build final attempt prompt with maximum strictness."""
        if not best_result:
            return base_prompt

        validation = best_result.get("validation", {})
        accuracy = validation.get("accuracy_score", 0)

        final_prompt = f"""
FINAL CRITICAL ATTEMPT - Previous best: {accuracy:.1f}%

THIS IS THE LAST CHANCE TO ACHIEVE 95%+ ACCURACY

{base_prompt}

ABSOLUTE REQUIREMENTS:
- MUST achieve 95%+ accuracy
- ZERO tolerance for format errors
- PERFECT delimiter usage
- COMPLETE factual preservation
- FLAWLESS structure compliance

FAILURE IS NOT AN OPTION - MAXIMUM PRECISION REQUIRED
"""

        return final_prompt

    def _validate_formatted_content(
        self, content: str, format_type: str, original_content: str
    ) -> Dict[str, Any]:
        """Validate formatted content for accuracy and compliance."""
        validation_result = {
            "is_valid": True,
            "accuracy_score": 100.0,
            "errors": [],
            "warnings": [],
        }

        # Format structure validation
        format_errors = self._validate_format_structure(content, format_type)
        if format_errors:
            validation_result["errors"].extend(format_errors)
            validation_result["accuracy_score"] -= len(format_errors) * 15

        # Content preservation validation
        preservation_score = self._calculate_content_preservation(
            content, original_content
        )
        if preservation_score < 90:
            validation_result["errors"].append(
                f"Content preservation too low: {preservation_score:.1f}%"
            )
            validation_result["accuracy_score"] = min(
                validation_result["accuracy_score"], preservation_score
            )

        # Final validation
        if validation_result["accuracy_score"] < 95.0 or validation_result["errors"]:
            validation_result["is_valid"] = False

        return validation_result

    def _validate_format_structure(self, content: str, format_type: str) -> List[str]:
        """Validate format structure and return errors."""
        errors = []

        if format_type == "qwen":
            if "<|user|>" not in content:
                errors.append("Missing <|user|> delimiter")
            if "<|assistant|>" not in content:
                errors.append("Missing <|assistant|> delimiter")

            # Check for proper structure
            pattern = r"<\|user\|>\s*(.+?)\s*<\|assistant\|>\s*(.+?)(?=<\|user\|>|$)"
            matches = re.findall(pattern, content, re.DOTALL)
            if not matches:
                errors.append("Invalid Qwen conversation structure")

        elif format_type == "alpaca":
            if not content.startswith("### Instruction:"):
                errors.append("Must start with ### Instruction:")
            if "### Response:" not in content:
                errors.append("Missing ### Response: section")

        elif format_type == "chatml":
            if "<|im_start|>" not in content:
                errors.append("Missing <|im_start|> delimiter")
            if "<|im_end|>" not in content:
                errors.append("Missing <|im_end|> delimiter")

            start_count = content.count("<|im_start|>")
            end_count = content.count("<|im_end|>")
            if start_count != end_count:
                errors.append("Mismatched <|im_start|> and <|im_end|> tags")

        return errors

    def _calculate_content_preservation(
        self, content: str, original_content: str
    ) -> float:
        """Calculate how well original content is preserved."""
        if not original_content:
            return 100.0

        # Simple word overlap calculation
        original_words = set(original_content.lower().split())
        content_words = set(content.lower().split())

        if not original_words:
            return 100.0

        overlap = len(original_words.intersection(content_words))
        preservation_score = (overlap / len(original_words)) * 100

        return min(100, preservation_score)

    def _analyze_and_correct(
        self, content: str, validation_result: Dict, format_type: str
    ) -> Dict[str, Any]:
        """Analyze validation result and prepare corrections."""
        corrections = []

        errors = validation_result.get("errors", [])
        for error in errors:
            if "delimiter" in error.lower():
                corrections.append(f"Fix delimiter issue: {error}")
            elif "structure" in error.lower():
                corrections.append(f"Fix structure issue: {error}")
            elif "preservation" in error.lower():
                corrections.append(f"Improve content preservation: {error}")

        return {
            "corrections": corrections,
            "priority_fixes": errors[:3],  # Top 3 priority fixes
        }
