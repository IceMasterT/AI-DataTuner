"""
Configuration settings for the Text Formatter application.
"""

# Text classification patterns
QUESTION_PATTERNS = [
    r'\?$',  # Ends with question mark
    r'^(what|how|why|when|where|who|which|can|could|would|should|do|does|did|is|are|was|were)\b',
    r'^(tell me|explain|describe|help me understand|show me|guide me)',
    r'^(please|could you|would you|can you)',
    r'(how to|what is|what are|how do|how does)',
]

ANSWER_PATTERNS = [
    r'^(the|this|that|it|you|your|according to|based on)',
    r'^(research shows|studies indicate|experts say|scientists believe)',
    r'^(in order to|to achieve|the key is|the solution)',
    r'^(first|second|third|next|then|finally)',
    r'\.$',  # Ends with period
    r'^[A-Z][^.!?]*[.!]$',  # Complete sentence
]

# Text processing settings
MIN_SEGMENT_LENGTH = 10  # Minimum characters for a valid segment
MAX_SEGMENT_LENGTH = 1000  # Maximum characters for a single segment

# Output formatting
USER_TAG = "<|user|>"
ASSISTANT_TAG = "<|assistant|>"
SEPARATOR = "\n\n"

# File processing
SUPPORTED_EXTENSIONS = ['.txt', '.md', '.text']
DEFAULT_ENCODING = 'utf-8'

# Advanced classification settings
CONTEXT_WEIGHT = 0.3  # How much to weight context in classification
PATTERN_WEIGHT = 0.7  # How much to weight pattern matching

# Debugging and logging
DEBUG_MODE = False
VERBOSE_OUTPUT = False
