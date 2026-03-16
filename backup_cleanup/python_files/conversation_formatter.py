#!/usr/bin/env python3
"""
Basic Conversation Formatter - Base class for conversation formatting.
Provides standard formatting methods for different conversation formats.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging


@dataclass
class FormattingResult:
    """Result from conversation formatting."""

    formatted_content: str
    format_type: str
    success: bool
    error_message: str = ""


class ConversationFormatter:
    """Basic conversation formatter for different formats."""

    def __init__(self, format_type: str = "qwen"):
        """Initialize the conversation formatter."""
        self.format_type = format_type
        self.logger = logging.getLogger(__name__)

        # Supported formats
        self.supported_formats = {
            "qwen",
            "alpaca",
            "chatml",
            "sharegpt",
            "llama2",
            "instruct",
            "gpt_jsonl",
        }

        if format_type not in self.supported_formats:
            self.logger.warning(
                f"Unsupported format: {format_type}, defaulting to qwen"
            )
            self.format_type = "qwen"

    def format_conversation(
        self, user_input: str, assistant_response: str, system_message: str = None
    ) -> FormattingResult:
        """
        Format a conversation according to the specified format.

        Args:
            user_input: User's input/question
            assistant_response: Assistant's response
            system_message: Optional system message

        Returns:
            FormattingResult with formatted content
        """
        try:
            if self.format_type == "qwen":
                formatted = self._format_qwen(
                    user_input, assistant_response, system_message
                )
            elif self.format_type == "alpaca":
                formatted = self._format_alpaca(user_input, assistant_response)
            elif self.format_type == "chatml":
                formatted = self._format_chatml(
                    user_input, assistant_response, system_message
                )
            elif self.format_type == "sharegpt":
                formatted = self._format_sharegpt(user_input, assistant_response)
            elif self.format_type == "llama2":
                formatted = self._format_llama2(user_input, assistant_response)
            elif self.format_type == "gpt_jsonl":
                formatted = self._format_gpt_jsonl(
                    user_input, assistant_response, system_message
                )
            elif self.format_type == "instruct":
                formatted = self._format_instruct(user_input, assistant_response)
            else:
                formatted = self._format_qwen(
                    user_input, assistant_response, system_message
                )

            return FormattingResult(
                formatted_content=formatted, format_type=self.format_type, success=True
            )

        except Exception as e:
            self.logger.error(f"Formatting failed: {e}")
            return FormattingResult(
                formatted_content="",
                format_type=self.format_type,
                success=False,
                error_message=str(e),
            )

    def _format_qwen(
        self, user_input: str, assistant_response: str, system_message: str = None
    ) -> str:
        """Format conversation in Qwen format."""
        formatted_parts = []

        if system_message:
            formatted_parts.append(f"<|system|>\n{system_message}")

        formatted_parts.append(f"<|user|>\n{user_input}")
        formatted_parts.append(f"<|assistant|>\n{assistant_response}")

        return "\n".join(formatted_parts)

    def _format_alpaca(self, user_input: str, assistant_response: str) -> str:
        """Format conversation in Alpaca format."""
        return f"### Instruction:\n{user_input}\n\n### Response:\n{assistant_response}"

    def _format_chatml(
        self, user_input: str, assistant_response: str, system_message: str = None
    ) -> str:
        """Format conversation in ChatML format."""
        formatted_parts = []

        if system_message:
            formatted_parts.append(f"<|im_start|>system\n{system_message}\n<|im_end|>")

        formatted_parts.append(f"<|im_start|>user\n{user_input}\n<|im_end|>")
        formatted_parts.append(
            f"<|im_start|>assistant\n{assistant_response}\n<|im_end|>"
        )

        return "\n".join(formatted_parts)

    def _format_sharegpt(self, user_input: str, assistant_response: str) -> str:
        """Format conversation in ShareGPT JSON format."""
        conversation = [
            {"from": "human", "value": user_input},
            {"from": "gpt", "value": assistant_response},
        ]

        return json.dumps(conversation, indent=2)

    def _format_llama2(self, user_input: str, assistant_response: str) -> str:
        """Format conversation in Llama-2 format."""
        return f"[INST] {user_input} [/INST] {assistant_response}"

    def _format_instruct(self, user_input: str, assistant_response: str) -> str:
        """Format conversation in simple instruction format."""
        return f"Question: {user_input}\n\nAnswer: {assistant_response}"

    def _format_gpt_jsonl(
        self, user_input: str, assistant_response: str, system_message: str = None
    ) -> str:
        """Format conversation in OpenAI ChatGPT fine-tuning JSONL object format."""
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "assistant", "content": assistant_response})
        return json.dumps({"messages": messages}, ensure_ascii=False)

    def format_multi_turn(
        self, conversations: List[Tuple[str, str]], system_message: str = None
    ) -> FormattingResult:
        """
        Format multi-turn conversation.

        Args:
            conversations: List of (user_input, assistant_response) tuples
            system_message: Optional system message

        Returns:
            FormattingResult with formatted multi-turn content
        """
        try:
            if self.format_type == "qwen":
                formatted = self._format_qwen_multi_turn(conversations, system_message)
            elif self.format_type == "alpaca":
                formatted = self._format_alpaca_multi_turn(conversations)
            elif self.format_type == "chatml":
                formatted = self._format_chatml_multi_turn(
                    conversations, system_message
                )
            elif self.format_type == "sharegpt":
                formatted = self._format_sharegpt_multi_turn(conversations)
            else:
                # For other formats, concatenate single turns
                formatted_turns = []
                for user_input, assistant_response in conversations:
                    result = self.format_conversation(
                        user_input, assistant_response, system_message
                    )
                    if result.success:
                        formatted_turns.append(result.formatted_content)

                formatted = "\n\n".join(formatted_turns)

            return FormattingResult(
                formatted_content=formatted, format_type=self.format_type, success=True
            )

        except Exception as e:
            self.logger.error(f"Multi-turn formatting failed: {e}")
            return FormattingResult(
                formatted_content="",
                format_type=self.format_type,
                success=False,
                error_message=str(e),
            )

    def _format_qwen_multi_turn(
        self, conversations: List[Tuple[str, str]], system_message: str = None
    ) -> str:
        """Format multi-turn conversation in Qwen format."""
        formatted_parts = []

        if system_message:
            formatted_parts.append(f"<|system|>\n{system_message}")

        for user_input, assistant_response in conversations:
            formatted_parts.append(f"<|user|>\n{user_input}")
            formatted_parts.append(f"<|assistant|>\n{assistant_response}")

        return "\n".join(formatted_parts)

    def _format_alpaca_multi_turn(self, conversations: List[Tuple[str, str]]) -> str:
        """Format multi-turn conversation in Alpaca format."""
        # Alpaca typically doesn't support multi-turn, so combine into single instruction
        combined_instruction = "Multi-turn conversation:\n"
        for i, (user_input, assistant_response) in enumerate(conversations, 1):
            combined_instruction += f"Turn {i} - User: {user_input}\n"
            combined_instruction += f"Turn {i} - Assistant: {assistant_response}\n"

        return f"### Instruction:\n{combined_instruction}\n\n### Response:\nI understand this multi-turn conversation."

    def _format_chatml_multi_turn(
        self, conversations: List[Tuple[str, str]], system_message: str = None
    ) -> str:
        """Format multi-turn conversation in ChatML format."""
        formatted_parts = []

        if system_message:
            formatted_parts.append(f"<|im_start|>system\n{system_message}\n<|im_end|>")

        for user_input, assistant_response in conversations:
            formatted_parts.append(f"<|im_start|>user\n{user_input}\n<|im_end|>")
            formatted_parts.append(
                f"<|im_start|>assistant\n{assistant_response}\n<|im_end|>"
            )

        return "\n".join(formatted_parts)

    def _format_sharegpt_multi_turn(self, conversations: List[Tuple[str, str]]) -> str:
        """Format multi-turn conversation in ShareGPT JSON format."""
        conversation = []

        for user_input, assistant_response in conversations:
            conversation.append({"from": "human", "value": user_input})
            conversation.append({"from": "gpt", "value": assistant_response})

        return json.dumps(conversation, indent=2)

    def validate_format(self, content: str) -> Dict[str, Any]:
        """
        Validate that content matches the expected format.

        Args:
            content: Content to validate

        Returns:
            Validation result with is_valid and errors
        """
        validation_result = {"is_valid": True, "errors": [], "warnings": []}

        try:
            if self.format_type == "qwen":
                validation_result = self._validate_qwen_format(content)
            elif self.format_type == "alpaca":
                validation_result = self._validate_alpaca_format(content)
            elif self.format_type == "chatml":
                validation_result = self._validate_chatml_format(content)
            elif self.format_type == "sharegpt":
                validation_result = self._validate_sharegpt_format(content)

        except Exception as e:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Validation error: {e}")

        return validation_result

    def _validate_qwen_format(self, content: str) -> Dict[str, Any]:
        """Validate Qwen format."""
        errors = []

        if "<|user|>" not in content:
            errors.append("Missing <|user|> delimiter")
        if "<|assistant|>" not in content:
            errors.append("Missing <|assistant|> delimiter")

        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": []}

    def _validate_alpaca_format(self, content: str) -> Dict[str, Any]:
        """Validate Alpaca format."""
        errors = []

        if not content.startswith("### Instruction:"):
            errors.append("Must start with ### Instruction:")
        if "### Response:" not in content:
            errors.append("Missing ### Response: section")

        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": []}

    def _validate_chatml_format(self, content: str) -> Dict[str, Any]:
        """Validate ChatML format."""
        errors = []

        start_count = content.count("<|im_start|>")
        end_count = content.count("<|im_end|>")

        if start_count == 0:
            errors.append("Missing <|im_start|> tags")
        if end_count == 0:
            errors.append("Missing <|im_end|> tags")
        if start_count != end_count:
            errors.append("Mismatched <|im_start|> and <|im_end|> tags")

        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": []}

    def _validate_sharegpt_format(self, content: str) -> Dict[str, Any]:
        """Validate ShareGPT JSON format."""
        errors = []

        try:
            data = json.loads(content)
            if not isinstance(data, list):
                errors.append("ShareGPT format must be a JSON array")
            else:
                for item in data:
                    if not isinstance(item, dict):
                        errors.append("Each conversation turn must be a JSON object")
                    elif "from" not in item or "value" not in item:
                        errors.append("Each turn must have 'from' and 'value' fields")
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")

        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": []}
