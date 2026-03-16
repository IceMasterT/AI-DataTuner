"""
Utility functions for text processing and analysis.
"""

import re
import string
from typing import List, Dict, Tuple
from config import MIN_SEGMENT_LENGTH, MAX_SEGMENT_LENGTH


def preprocess_text(text: str) -> str:
    """
    Preprocess raw text for better classification.
    
    Args:
        text: Raw input text
        
    Returns:
        Cleaned and normalized text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Fix common formatting issues
    text = re.sub(r'([.!?])\s*([a-z])', r'\1 \2', text)  # Space after punctuation
    text = re.sub(r'([a-z])([A-Z])', r'\1. \2', text)    # Add period between sentences
    
    # Remove formatting artifacts
    text = re.sub(r'^\d+\.\s*', '', text)  # Remove numbered list items
    text = re.sub(r'^[-*•]\s*', '', text)   # Remove bullet points
    text = re.sub(r'^>\s*', '', text)       # Remove quote markers
    
    return text


def split_text_intelligently(text: str) -> List[str]:
    """
    Split text into logical segments using multiple strategies.

    Args:
        text: Input text to split

    Returns:
        List of text segments
    """
    segments = []

    # First, split by double newlines (paragraphs)
    paragraphs = text.split('\n\n')

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # Split by question marks followed by space and capital letter or new sentence
        # This pattern captures: "Question? Answer starts here" or "Question? Next question"
        parts = re.split(r'(\?)\s+(?=[A-Z])', paragraph)

        current_segment = ""
        for part in parts:
            if part == '?':
                # Add the question mark to current segment and finalize it
                current_segment += part
                if current_segment.strip():
                    segments.append(current_segment.strip())
                current_segment = ""
            else:
                current_segment += part

        # Add any remaining content
        if current_segment.strip():
            segments.append(current_segment.strip())

    # Filter out segments that are too short and clean them
    final_segments = []
    for seg in segments:
        seg = seg.strip()
        if len(seg) >= MIN_SEGMENT_LENGTH:
            final_segments.append(seg)

    return final_segments


def split_by_sentences(text: str) -> List[str]:
    """
    Split text by sentences, handling edge cases.
    
    Args:
        text: Input text
        
    Returns:
        List of sentences
    """
    # Split by sentence-ending punctuation followed by space and capital letter
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    
    # Clean up sentences
    sentences = [sent.strip() for sent in sentences if sent.strip()]
    
    return sentences


def calculate_text_features(text: str) -> Dict[str, float]:
    """
    Calculate features for text classification.
    
    Args:
        text: Input text
        
    Returns:
        Dictionary of text features
    """
    text_lower = text.lower().strip()
    
    features = {
        'length': len(text),
        'word_count': len(text.split()),
        'question_mark_count': text.count('?'),
        'exclamation_count': text.count('!'),
        'period_count': text.count('.'),
        'starts_with_capital': text[0].isupper() if text else False,
        'ends_with_question': text.endswith('?'),
        'ends_with_period': text.endswith('.'),
        'ends_with_exclamation': text.endswith('!'),
        'has_question_words': any(word in text_lower for word in 
                                ['what', 'how', 'why', 'when', 'where', 'who', 'which']),
        'has_modal_verbs': any(word in text_lower for word in 
                             ['can', 'could', 'would', 'should', 'might', 'may']),
        'has_imperative_words': any(word in text_lower for word in 
                                  ['please', 'tell', 'explain', 'describe', 'show']),
    }
    
    return features


def score_as_question(text: str) -> float:
    """
    Calculate probability that text is a question.
    
    Args:
        text: Input text
        
    Returns:
        Score between 0 and 1 (higher = more likely to be question)
    """
    features = calculate_text_features(text)
    score = 0.0
    
    # Question mark is strong indicator
    if features['ends_with_question']:
        score += 0.8
    
    # Question words
    if features['has_question_words']:
        score += 0.3
    
    # Modal verbs (can, could, would, etc.)
    if features['has_modal_verbs']:
        score += 0.2
    
    # Imperative words
    if features['has_imperative_words']:
        score += 0.2
    
    # Length factor (questions tend to be shorter)
    if features['word_count'] < 20:
        score += 0.1
    
    return min(score, 1.0)


def score_as_answer(text: str) -> float:
    """
    Calculate probability that text is an answer.

    Args:
        text: Input text

    Returns:
        Score between 0 and 1 (higher = more likely to be answer)
    """
    features = calculate_text_features(text)
    text_lower = text.lower().strip()
    score = 0.0

    # Ends with period (declarative)
    if features['ends_with_period']:
        score += 0.4

    # Starts with definitive words
    definitive_starters = ['the', 'this', 'that', 'it', 'you', 'your', 'according to', 'based on']
    if any(text_lower.startswith(starter) for starter in definitive_starters):
        score += 0.4

    # Contains explanatory phrases
    explanatory_phrases = ['because', 'therefore', 'as a result', 'in order to', 'due to']
    if any(phrase in text_lower for phrase in explanatory_phrases):
        score += 0.2

    # Length factor (answers tend to be longer)
    if features['word_count'] > 15:
        score += 0.2

    # Multiple sentences (complex answers)
    if features['period_count'] > 1:
        score += 0.1

    return min(score, 1.0)


def validate_input(text: str) -> Tuple[bool, str]:
    """
    Validate input text.
    
    Args:
        text: Input text to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text or not text.strip():
        return False, "Input text is empty"
    
    if len(text.strip()) < MIN_SEGMENT_LENGTH:
        return False, f"Input text is too short (minimum {MIN_SEGMENT_LENGTH} characters)"
    
    # Check for reasonable text content
    if not re.search(r'[a-zA-Z]', text):
        return False, "Input text contains no alphabetic characters"
    
    return True, ""


def format_output(segments: List[Tuple[str, str]], separator: str = "\n\n") -> str:
    """
    Format classified segments into final output.
    
    Args:
        segments: List of (role, content) tuples
        separator: String to separate conversation turns
        
    Returns:
        Formatted conversation string
    """
    formatted_lines = []
    
    for role, content in segments:
        # Ensure content is properly formatted
        content = content.strip()
        if not content.endswith(('.', '!', '?')):
            content += '.'
        
        formatted_lines.append(f"<|{role}|> {content}")
    
    return separator.join(formatted_lines)
