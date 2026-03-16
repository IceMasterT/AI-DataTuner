#!/usr/bin/env python3
"""
Automated Text Classification and Formatting Tool
Converts raw text into conversational format with <|user|> and <|assistant|> tags.
"""

import re
import argparse
import sys
from typing import List, Tuple, Dict
from pathlib import Path
from utils import (
    preprocess_text, split_text_intelligently, score_as_question,
    score_as_answer, validate_input, format_output
)
from config import QUESTION_PATTERNS, ANSWER_PATTERNS, CONTEXT_WEIGHT, PATTERN_WEIGHT
from format_templates import FormatFactory, ConversationFormat


class AdvancedTextClassifier:
    """Advanced text classifier using multiple strategies."""

    def __init__(self):
        self.question_patterns = QUESTION_PATTERNS
        self.answer_patterns = ANSWER_PATTERNS
        self.context_weight = CONTEXT_WEIGHT
        self.pattern_weight = PATTERN_WEIGHT

    def classify_text(self, text: str, context: List[str] = None) -> str:
        """
        Classify text as 'user' (question) or 'assistant' (answer).

        Args:
            text: Text to classify
            context: Previous text segments for context

        Returns:
            'user' or 'assistant'
        """
        # Get scores from utility functions
        question_score = score_as_question(text)
        answer_score = score_as_answer(text)

        # Apply pattern matching
        pattern_question_score = self._pattern_match_question(text)
        pattern_answer_score = self._pattern_match_answer(text)

        # Combine scores with higher weight on utility functions
        final_question_score = (
            question_score * 0.7 +
            pattern_question_score * 0.3
        )
        final_answer_score = (
            answer_score * 0.7 +
            pattern_answer_score * 0.3
        )

        # Use context if available (alternating pattern)
        if context and len(context) > 0:
            last_classification = self._get_last_classification(context)
            if last_classification == "user":
                final_answer_score += 0.3  # Bias toward answer after question
            else:
                final_question_score += 0.2  # Slight bias toward question after answer

        # Strong question indicators override other factors
        if text.strip().endswith('?'):
            final_question_score += 0.5

        # Make decision with minimum threshold
        if final_question_score > final_answer_score and final_question_score > 0.4:
            return "user"
        elif final_answer_score > 0.3:
            return "assistant"
        else:
            # Default based on context or fallback to user
            if context and len(context) > 0:
                last_classification = self._get_last_classification(context)
                return "assistant" if last_classification == "user" else "user"
            return "user"

    def _pattern_match_question(self, text: str) -> float:
        """Pattern matching for questions."""
        text_clean = text.strip().lower()
        score = 0.0

        for pattern in self.question_patterns:
            if re.search(pattern, text_clean, re.IGNORECASE):
                score += 0.2

        return min(score, 1.0)

    def _pattern_match_answer(self, text: str) -> float:
        """Pattern matching for answers."""
        text_clean = text.strip().lower()
        score = 0.0

        for pattern in self.answer_patterns:
            if re.search(pattern, text_clean, re.IGNORECASE):
                score += 0.2

        return min(score, 1.0)

    def _get_context_bias(self, context: List[str]) -> float:
        """Get bias based on context (alternating pattern)."""
        if not context:
            return 0.0

        # If last was question, bias toward answer
        last_text = context[-1] if context else ""
        if score_as_question(last_text) > 0.5:
            return -0.3  # Bias toward answer
        else:
            return 0.3   # Bias toward question

    def _get_last_classification(self, context: List[str]) -> str:
        """Get the classification of the last context item."""
        if not context:
            return "user"

        last_text = context[-1]
        question_score = score_as_question(last_text)
        answer_score = score_as_answer(last_text)

        if last_text.strip().endswith('?') or question_score > answer_score:
            return "user"
        else:
            return "assistant"


class ConversationFormatter:
    """Formats text into conversation format with multiple format support."""

    def __init__(self, output_format: str = "qwen", **format_kwargs):
        self.classifier = AdvancedTextClassifier()
        self.output_format = output_format
        self.format_kwargs = format_kwargs

        # Create format template
        try:
            format_enum = ConversationFormat(output_format.lower())
            self.template = FormatFactory.create_template(format_enum, **format_kwargs)
        except ValueError:
            # Default to Qwen format if invalid format specified
            self.template = FormatFactory.create_template(ConversationFormat.QWEN)

    def split_into_segments(self, text: str) -> List[str]:
        """Split text into logical segments."""
        # Use the intelligent splitting from utils
        return split_text_intelligently(preprocess_text(text))

    def classify_segments(self, segments: List[str]) -> List[Tuple[str, str]]:
        """Classify segments as questions or answers."""
        classified = []
        context = []

        for segment in segments:
            # Get classification using context
            role = self.classifier.classify_text(segment, context)
            classified.append((role, segment))
            context.append(segment)

        return classified

    def format_conversation(self, classified_segments: List[Tuple[str, str]]) -> str:
        """Format classified segments into conversation format."""
        return self.template.format_conversation(classified_segments)

    def process_text(self, raw_text: str) -> str:
        """Main processing pipeline."""
        # Validate input
        is_valid, error_msg = validate_input(raw_text)
        if not is_valid:
            raise ValueError(f"Invalid input: {error_msg}")

        # Split text into segments
        segments = self.split_into_segments(raw_text)

        # Classify segments
        classified = self.classify_segments(segments)

        # Format as conversation
        formatted = self.format_conversation(classified)

        return formatted

    def get_available_formats(self) -> List[str]:
        """Get list of available output formats."""
        return FormatFactory.get_available_formats()

    def get_format_description(self, format_name: str) -> str:
        """Get description of a format."""
        try:
            format_enum = ConversationFormat(format_name.lower())
            return FormatFactory.get_format_description(format_enum)
        except ValueError:
            return "Unknown format"


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="Automated Text Classification and Formatting Tool"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input file path or text (use '-' for stdin)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "-t", "--text",
        help="Process text directly from command line"
    )
    parser.add_argument(
        "-f", "--format",
        default="qwen",
        choices=FormatFactory.get_available_formats(),
        help="Output format (default: qwen)"
    )
    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="List all available formats and exit"
    )
    parser.add_argument(
        "--system-message",
        help="System message for OpenAI format (optional)"
    )

    args = parser.parse_args()

    # List formats if requested
    if args.list_formats:
        print("Available conversation formats:")
        print("-" * 40)
        for fmt in FormatFactory.get_available_formats():
            try:
                format_enum = ConversationFormat(fmt)
                description = FormatFactory.get_format_description(format_enum)
                print(f"{fmt:12} - {description}")
            except ValueError:
                continue
        return 0
    
    # Get input text
    if args.text:
        raw_text = args.text
    elif args.input == "-" or not args.input:
        raw_text = sys.stdin.read()
    else:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                raw_text = f.read()
        except FileNotFoundError:
            print(f"Error: File '{args.input}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

    if not raw_text.strip():
        print("Error: No input text provided.", file=sys.stderr)
        sys.exit(1)

    # Prepare format kwargs
    format_kwargs = {}
    if args.system_message and args.format == "openai":
        format_kwargs["system_message"] = args.system_message

    # Process text
    formatter = ConversationFormatter(output_format=args.format, **format_kwargs)
    formatted_text = formatter.process_text(raw_text)
    
    # Output result
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
            print(f"Formatted text saved to: {args.output}")
        except Exception as e:
            print(f"Error writing to file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(formatted_text)


if __name__ == "__main__":
    main()
