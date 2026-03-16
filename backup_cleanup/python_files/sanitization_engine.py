#!/usr/bin/env python3
"""
Core text sanitization engine for LLM training data.
Protects against adversarial Unicode, malformed content, and data corruption.
"""

import unicodedata
import re
import math
import json
import html
from typing import Dict, List, Tuple, Optional, Set
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class ThreatLevel(Enum):
    """Threat severity levels."""
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    DANGEROUS = "dangerous"
    CORRUPTED = "corrupted"


class ThreatType(Enum):
    """Types of threats detected."""
    INVISIBLE_CHARS = "invisible_characters"
    DIRECTION_OVERRIDE = "direction_override"
    HOMOGLYPHS = "homoglyphs"
    TOKEN_POLLUTION = "token_pollution"
    LOW_ENTROPY = "low_entropy"
    HIGH_ENTROPY = "high_entropy"
    MALFORMED_MARKUP = "malformed_markup"
    ENCODING_CORRUPTION = "encoding_corruption"
    REPEATED_TOKENS = "repeated_tokens"
    SUSPICIOUS_UNICODE = "suspicious_unicode"


@dataclass
class SanitizationResult:
    """Result of text sanitization."""
    original_text: str
    sanitized_text: Optional[str]
    threat_level: ThreatLevel
    threats_detected: List[ThreatType]
    details: Dict[str, any]
    timestamp: datetime
    action_taken: str


class CoreSanitizer:
    """Core text sanitization engine."""
    
    def __init__(self):
        # Invisible and problematic Unicode characters
        self.invisible_chars = {
            '\u200B',  # Zero Width Space
            '\u200C',  # Zero Width Non-Joiner
            '\u200D',  # Zero Width Joiner
            '\u2060',  # Word Joiner
            '\uFEFF',  # Zero Width No-Break Space (BOM)
            '\u00AD',  # Soft Hyphen
            '\u034F',  # Combining Grapheme Joiner
            '\u061C',  # Arabic Letter Mark
            '\u180E',  # Mongolian Vowel Separator
        }
        
        # Direction override characters
        self.direction_overrides = {
            '\u202A',  # Left-to-Right Embedding
            '\u202B',  # Right-to-Left Embedding
            '\u202C',  # Pop Directional Formatting
            '\u202D',  # Left-to-Right Override
            '\u202E',  # Right-to-Left Override
            '\u2066',  # Left-to-Right Isolate
            '\u2067',  # Right-to-Left Isolate
            '\u2068',  # First Strong Isolate
            '\u2069',  # Pop Directional Isolate
        }
        
        # Suspicious Unicode ranges
        self.suspicious_ranges = [
            (0x1D400, 0x1D7FF),  # Mathematical symbols
            (0x1F600, 0x1F64F),  # Emoticons (excessive use)
            (0x2700, 0x27BF),    # Dingbats
            (0x1F300, 0x1F5FF),  # Miscellaneous symbols
        ]
        
        # Common homoglyph mappings (basic set)
        self.homoglyph_map = {
            'а': 'a',  # Cyrillic a -> Latin a
            'е': 'e',  # Cyrillic e -> Latin e
            'о': 'o',  # Cyrillic o -> Latin o
            'р': 'p',  # Cyrillic p -> Latin p
            'с': 'c',  # Cyrillic c -> Latin c
            'х': 'x',  # Cyrillic x -> Latin x
            'у': 'y',  # Cyrillic y -> Latin y
            'ο': 'o',  # Greek omicron -> Latin o
            'α': 'a',  # Greek alpha -> Latin a
        }
    
    def normalize_unicode(self, text: str) -> str:
        """Normalize Unicode text to NFKC form."""
        try:
            return unicodedata.normalize("NFKC", text)
        except Exception:
            return text
    
    def remove_invisible_characters(self, text: str) -> Tuple[str, List[str]]:
        """Remove invisible characters and return cleaned text with details."""
        found_chars = []
        cleaned_text = text
        
        for char in self.invisible_chars:
            if char in text:
                found_chars.append(f"U+{ord(char):04X}")
                cleaned_text = cleaned_text.replace(char, '')
        
        return cleaned_text, found_chars
    
    def detect_direction_overrides(self, text: str) -> List[str]:
        """Detect direction override characters."""
        found_overrides = []
        
        for char in self.direction_overrides:
            if char in text:
                found_overrides.append(f"U+{ord(char):04X}")
        
        return found_overrides
    
    def detect_homoglyphs(self, text: str) -> Tuple[str, List[str]]:
        """Detect and optionally normalize homoglyphs."""
        found_homoglyphs = []
        normalized_text = text
        
        for homoglyph, replacement in self.homoglyph_map.items():
            if homoglyph in text:
                found_homoglyphs.append(f"{homoglyph} -> {replacement}")
                normalized_text = normalized_text.replace(homoglyph, replacement)
        
        return normalized_text, found_homoglyphs
    
    def calculate_shannon_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
        
        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Calculate probabilities and entropy
        text_length = len(text)
        entropy = 0.0
        
        for count in char_counts.values():
            probability = count / text_length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def detect_token_pollution(self, text: str) -> Dict[str, any]:
        """Detect various forms of token pollution."""
        issues = {}
        
        # Check for excessive non-ASCII characters
        non_ascii_count = sum(1 for char in text if ord(char) > 127)
        non_ascii_ratio = non_ascii_count / len(text) if text else 0
        
        if non_ascii_ratio > 0.5:
            issues['high_non_ascii_ratio'] = non_ascii_ratio
        
        # Check for repeated characters
        if text:
            char_counts = {char: text.count(char) for char in set(text)}
            max_repetition = max(char_counts.values())
            
            if max_repetition > len(text) * 0.3:  # More than 30% of text is one character
                most_repeated = max(char_counts, key=char_counts.get)
                issues['excessive_repetition'] = {
                    'character': most_repeated,
                    'count': max_repetition,
                    'ratio': max_repetition / len(text)
                }
        
        # Check for suspicious Unicode ranges
        suspicious_chars = []
        for char in text:
            char_code = ord(char)
            for start, end in self.suspicious_ranges:
                if start <= char_code <= end:
                    suspicious_chars.append(f"U+{char_code:04X}")
        
        if suspicious_chars:
            issues['suspicious_unicode'] = suspicious_chars[:10]  # Limit to first 10
        
        return issues
    
    def detect_repeated_tokens(self, text: str) -> Dict[str, any]:
        """Detect repeated words or tokens."""
        words = text.split()
        if len(words) < 3:
            return {}
        
        word_counts = {}
        for word in words:
            word_lower = word.lower()
            word_counts[word_lower] = word_counts.get(word_lower, 0) + 1
        
        # Find words that appear too frequently
        total_words = len(words)
        repeated_tokens = {}
        
        for word, count in word_counts.items():
            ratio = count / total_words
            if ratio > 0.2 and count > 3:  # More than 20% and at least 4 times
                repeated_tokens[word] = {'count': count, 'ratio': ratio}
        
        return repeated_tokens if repeated_tokens else {}
    
    def validate_encoding(self, text: str) -> List[str]:
        """Check for encoding corruption issues."""
        issues = []
        
        # Check for common encoding corruption patterns
        corruption_patterns = [
            r'Ã¢â‚¬â„¢',  # Smart quote corruption
            r'Ã¢â‚¬Â',     # Em dash corruption
            r'Ã©',          # é corruption
            r'Ã¡',          # á corruption
            r'â€™',         # Right single quotation mark
            r'â€œ',         # Left double quotation mark
            r'â€\x9d',      # Right double quotation mark
        ]
        
        for pattern in corruption_patterns:
            if re.search(pattern, text):
                issues.append(f"Encoding corruption pattern: {pattern}")
        
        # Check for replacement characters
        if '\uFFFD' in text:  # Unicode replacement character
            issues.append("Unicode replacement character found")
        
        return issues
    
    def sanitize_text(self, text: str, aggressive: bool = False) -> SanitizationResult:
        """
        Main sanitization function.
        
        Args:
            text: Input text to sanitize
            aggressive: Whether to apply aggressive filtering
            
        Returns:
            SanitizationResult with details of sanitization
        """
        if not isinstance(text, str):
            return SanitizationResult(
                original_text=str(text),
                sanitized_text=None,
                threat_level=ThreatLevel.CORRUPTED,
                threats_detected=[ThreatType.ENCODING_CORRUPTION],
                details={'error': 'Input is not a string'},
                timestamp=datetime.now(),
                action_taken='rejected'
            )
        
        threats_detected = []
        details = {}
        sanitized_text = text
        
        # Step 1: Unicode normalization
        sanitized_text = self.normalize_unicode(sanitized_text)
        
        # Step 2: Remove invisible characters
        sanitized_text, invisible_found = self.remove_invisible_characters(sanitized_text)
        if invisible_found:
            threats_detected.append(ThreatType.INVISIBLE_CHARS)
            details['invisible_characters'] = invisible_found
        
        # Step 3: Check for direction overrides
        direction_overrides = self.detect_direction_overrides(sanitized_text)
        if direction_overrides:
            threats_detected.append(ThreatType.DIRECTION_OVERRIDE)
            details['direction_overrides'] = direction_overrides
        
        # Step 4: Handle homoglyphs
        sanitized_text, homoglyphs_found = self.detect_homoglyphs(sanitized_text)
        if homoglyphs_found:
            threats_detected.append(ThreatType.HOMOGLYPHS)
            details['homoglyphs'] = homoglyphs_found
        
        # Step 5: Check entropy
        entropy = self.calculate_shannon_entropy(sanitized_text)
        details['entropy'] = entropy
        
        if entropy < 2.0:
            threats_detected.append(ThreatType.LOW_ENTROPY)
        elif entropy > 7.0:
            threats_detected.append(ThreatType.HIGH_ENTROPY)
        
        # Step 6: Token pollution detection
        pollution_issues = self.detect_token_pollution(sanitized_text)
        if pollution_issues:
            threats_detected.append(ThreatType.TOKEN_POLLUTION)
            details['token_pollution'] = pollution_issues
        
        # Step 7: Repeated tokens
        repeated_tokens = self.detect_repeated_tokens(sanitized_text)
        if repeated_tokens:
            threats_detected.append(ThreatType.REPEATED_TOKENS)
            details['repeated_tokens'] = repeated_tokens
        
        # Step 8: Encoding validation
        encoding_issues = self.validate_encoding(sanitized_text)
        if encoding_issues:
            threats_detected.append(ThreatType.ENCODING_CORRUPTION)
            details['encoding_issues'] = encoding_issues
        
        # Determine threat level and action
        threat_level = self._assess_threat_level(threats_detected, aggressive)
        action_taken = self._determine_action(threat_level, aggressive)
        
        # Apply action
        if action_taken == 'reject':
            sanitized_text = None
        elif action_taken == 'quarantine':
            sanitized_text = None  # Will be stored in quarantine
        
        return SanitizationResult(
            original_text=text,
            sanitized_text=sanitized_text,
            threat_level=threat_level,
            threats_detected=threats_detected,
            details=details,
            timestamp=datetime.now(),
            action_taken=action_taken
        )
    
    def _assess_threat_level(self, threats: List[ThreatType], aggressive: bool) -> ThreatLevel:
        """Assess overall threat level based on detected threats."""
        if not threats:
            return ThreatLevel.CLEAN
        
        dangerous_threats = {
            ThreatType.DIRECTION_OVERRIDE,
            ThreatType.ENCODING_CORRUPTION,
        }
        
        suspicious_threats = {
            ThreatType.INVISIBLE_CHARS,
            ThreatType.HOMOGLYPHS,
            ThreatType.TOKEN_POLLUTION,
            ThreatType.REPEATED_TOKENS,
        }
        
        if any(threat in dangerous_threats for threat in threats):
            return ThreatLevel.DANGEROUS
        
        if aggressive and any(threat in suspicious_threats for threat in threats):
            return ThreatLevel.DANGEROUS
        
        if any(threat in suspicious_threats for threat in threats):
            return ThreatLevel.SUSPICIOUS
        
        return ThreatLevel.SUSPICIOUS
    
    def _determine_action(self, threat_level: ThreatLevel, aggressive: bool) -> str:
        """Determine what action to take based on threat level."""
        if threat_level == ThreatLevel.CLEAN:
            return 'accept'
        elif threat_level == ThreatLevel.SUSPICIOUS:
            return 'quarantine' if aggressive else 'accept_with_warning'
        elif threat_level == ThreatLevel.DANGEROUS:
            return 'reject'
        else:  # CORRUPTED
            return 'reject'
