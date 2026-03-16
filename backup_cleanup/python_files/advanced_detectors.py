#!/usr/bin/env python3
"""
Advanced detection algorithms for sophisticated threats in text data.
Includes ML-based detection, statistical analysis, and pattern recognition.
"""

import re
import math
import statistics
from typing import Dict, List, Tuple, Optional, Set
from collections import Counter, defaultdict
import unicodedata
from datetime import datetime


class AdvancedThreatDetector:
    """Advanced algorithms for detecting sophisticated text-based threats."""
    
    def __init__(self):
        # Extended homoglyph database
        self.homoglyph_database = self._build_homoglyph_database()
        
        # Suspicious pattern database
        self.suspicious_patterns = self._build_suspicious_patterns()
        
        # Language detection patterns
        self.language_patterns = self._build_language_patterns()
        
        # Common adversarial techniques
        self.adversarial_patterns = self._build_adversarial_patterns()
    
    def _build_homoglyph_database(self) -> Dict[str, List[str]]:
        """Build comprehensive homoglyph database."""
        return {
            'a': ['а', 'α', 'ɑ', 'ａ'],  # Latin a variants
            'e': ['е', 'ε', 'ｅ'],        # Latin e variants
            'o': ['о', 'ο', 'ο', 'ｏ'],   # Latin o variants
            'p': ['р', 'ρ', 'ｐ'],        # Latin p variants
            'c': ['с', 'ϲ', 'ｃ'],        # Latin c variants
            'x': ['х', 'χ', 'ｘ'],        # Latin x variants
            'y': ['у', 'γ', 'ｙ'],        # Latin y variants
            'i': ['і', 'ι', 'ｉ'],        # Latin i variants
            'n': ['п', 'η', 'ｎ'],        # Latin n variants
            'm': ['м', 'μ', 'ｍ'],        # Latin m variants
            'h': ['һ', 'η', 'ｈ'],        # Latin h variants
            'k': ['к', 'κ', 'ｋ'],        # Latin k variants
            'b': ['в', 'β', 'ｂ'],        # Latin b variants
            't': ['т', 'τ', 'ｔ'],        # Latin t variants
            'r': ['г', 'ρ', 'ｒ'],        # Latin r variants
            's': ['ѕ', 'σ', 'ｓ'],        # Latin s variants
        }
    
    def _build_suspicious_patterns(self) -> List[str]:
        """Build patterns for suspicious content."""
        return [
            r'(.)\1{10,}',                    # Character repeated 10+ times
            r'\b(\w+)\s+\1\s+\1\b',          # Word repeated 3+ times
            r'[^\x00-\x7F]{20,}',            # Long non-ASCII sequences
            r'[\u2000-\u206F]{3,}',          # Multiple general punctuation
            r'[\u2700-\u27BF]{5,}',          # Excessive dingbats
            r'[\u1F600-\u1F64F]{10,}',       # Emoji spam
            r'[A-Z]{50,}',                   # Excessive caps
            r'\d{100,}',                     # Very long numbers
            r'[!@#$%^&*()]{20,}',           # Symbol spam
            r'(.{1,3})\1{20,}',             # Pattern repetition
        ]
    
    def _build_language_patterns(self) -> Dict[str, str]:
        """Build language detection patterns."""
        return {
            'mixed_scripts': r'[\u0400-\u04FF].*[a-zA-Z]|[a-zA-Z].*[\u0400-\u04FF]',  # Cyrillic + Latin
            'arabic_latin': r'[\u0600-\u06FF].*[a-zA-Z]|[a-zA-Z].*[\u0600-\u06FF]',   # Arabic + Latin
            'chinese_latin': r'[\u4e00-\u9fff].*[a-zA-Z]|[a-zA-Z].*[\u4e00-\u9fff]', # Chinese + Latin
            'excessive_diacritics': r'[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{10,}',
        }
    
    def _build_adversarial_patterns(self) -> Dict[str, str]:
        """Build patterns for known adversarial techniques."""
        return {
            'leetspeak': r'\b[a-z]*[0-9]+[a-z]*[0-9]+[a-z]*\b',  # h3ll0, n1c3
            'zalgo_text': r'[\u0300-\u036F]{3,}',                # Combining diacritics
            'fullwidth': r'[\uFF00-\uFFEF]{5,}',                 # Fullwidth characters
            'enclosed': r'[\u2460-\u24FF]{3,}',                  # Enclosed alphanumerics
            'mathematical': r'[\u1D400-\u1D7FF]{5,}',           # Mathematical symbols
            'variation_selectors': r'[\uFE00-\uFE0F\U000E0100-\U000E01EF]', # Variation selectors
        }
    
    def detect_advanced_homoglyphs(self, text: str) -> Dict[str, any]:
        """Advanced homoglyph detection using comprehensive database."""
        detected = {}
        homoglyph_count = 0
        replacements = []
        
        for char in text:
            for latin_char, variants in self.homoglyph_database.items():
                if char in variants:
                    homoglyph_count += 1
                    replacements.append(f"{char} (U+{ord(char):04X}) -> {latin_char}")
        
        if homoglyph_count > 0:
            detected['count'] = homoglyph_count
            detected['ratio'] = homoglyph_count / len(text) if text else 0
            detected['replacements'] = replacements[:20]  # Limit output
            detected['severity'] = 'high' if homoglyph_count > len(text) * 0.1 else 'medium'
        
        return detected
    
    def detect_script_mixing(self, text: str) -> Dict[str, any]:
        """Detect suspicious mixing of different writing scripts."""
        scripts = defaultdict(int)
        
        for char in text:
            if char.isalpha():
                script = unicodedata.name(char, '').split()[0] if unicodedata.name(char, '') else 'UNKNOWN'
                scripts[script] += 1
        
        if len(scripts) <= 1:
            return {}
        
        total_chars = sum(scripts.values())
        script_ratios = {script: count/total_chars for script, count in scripts.items()}
        
        # Check for suspicious mixing patterns
        suspicious_mixing = {}
        
        # Latin + Cyrillic mixing (common in attacks)
        latin_ratio = script_ratios.get('LATIN', 0)
        cyrillic_ratio = script_ratios.get('CYRILLIC', 0)
        
        if latin_ratio > 0.1 and cyrillic_ratio > 0.1:
            suspicious_mixing['latin_cyrillic'] = {
                'latin_ratio': latin_ratio,
                'cyrillic_ratio': cyrillic_ratio,
                'severity': 'high'
            }
        
        # Check for other suspicious combinations
        for pattern_name, pattern in self.language_patterns.items():
            if re.search(pattern, text):
                suspicious_mixing[pattern_name] = {'detected': True}
        
        return suspicious_mixing
    
    def analyze_character_distribution(self, text: str) -> Dict[str, any]:
        """Analyze character distribution for anomalies."""
        if not text:
            return {}
        
        char_counts = Counter(text)
        total_chars = len(text)
        
        analysis = {}
        
        # Calculate character frequency statistics
        frequencies = list(char_counts.values())
        analysis['mean_frequency'] = statistics.mean(frequencies)
        analysis['median_frequency'] = statistics.median(frequencies)
        analysis['std_frequency'] = statistics.stdev(frequencies) if len(frequencies) > 1 else 0
        
        # Find outliers (characters appearing much more than expected)
        outliers = []
        for char, count in char_counts.items():
            frequency = count / total_chars
            if frequency > 0.2:  # More than 20% of text
                outliers.append({
                    'char': char,
                    'unicode': f"U+{ord(char):04X}",
                    'count': count,
                    'frequency': frequency
                })
        
        if outliers:
            analysis['outliers'] = outliers
        
        # Check for uniform distribution (possible random data)
        unique_chars = len(char_counts)
        expected_frequency = 1 / unique_chars if unique_chars > 0 else 0
        variance = sum((freq/total_chars - expected_frequency)**2 for freq in frequencies) / unique_chars
        
        if variance < 0.001 and unique_chars > 10:  # Very uniform distribution
            analysis['uniform_distribution'] = {
                'variance': variance,
                'unique_chars': unique_chars,
                'suspicion': 'possible_random_data'
            }
        
        return analysis
    
    def detect_adversarial_patterns(self, text: str) -> Dict[str, any]:
        """Detect known adversarial text patterns."""
        detected_patterns = {}
        
        # Check each adversarial pattern
        for pattern_name, pattern in self.adversarial_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                detected_patterns[pattern_name] = {
                    'matches': len(matches),
                    'examples': matches[:5]  # First 5 examples
                }
        
        # Check suspicious patterns
        for i, pattern in enumerate(self.suspicious_patterns):
            matches = re.findall(pattern, text)
            if matches:
                pattern_name = f"suspicious_pattern_{i+1}"
                detected_patterns[pattern_name] = {
                    'pattern': pattern,
                    'matches': len(matches),
                    'examples': matches[:3]
                }
        
        return detected_patterns
    
    def analyze_entropy_distribution(self, text: str, window_size: int = 50) -> Dict[str, any]:
        """Analyze entropy distribution across text windows."""
        if len(text) < window_size:
            return {}
        
        entropies = []
        
        # Calculate entropy for sliding windows
        for i in range(0, len(text) - window_size + 1, window_size // 2):
            window = text[i:i + window_size]
            entropy = self._calculate_window_entropy(window)
            entropies.append(entropy)
        
        if not entropies:
            return {}
        
        analysis = {
            'mean_entropy': statistics.mean(entropies),
            'min_entropy': min(entropies),
            'max_entropy': max(entropies),
            'entropy_variance': statistics.variance(entropies) if len(entropies) > 1 else 0
        }
        
        # Detect anomalous entropy patterns
        if analysis['entropy_variance'] > 2.0:
            analysis['high_variance'] = True
            analysis['suspicion'] = 'inconsistent_randomness'
        
        if analysis['min_entropy'] < 1.0:
            analysis['very_low_entropy_regions'] = True
            analysis['suspicion'] = 'possible_repeated_content'
        
        if analysis['max_entropy'] > 6.0:
            analysis['very_high_entropy_regions'] = True
            analysis['suspicion'] = 'possible_random_data'
        
        return analysis
    
    def _calculate_window_entropy(self, text: str) -> float:
        """Calculate Shannon entropy for a text window."""
        if not text:
            return 0.0
        
        char_counts = Counter(text)
        text_length = len(text)
        
        entropy = 0.0
        for count in char_counts.values():
            probability = count / text_length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def detect_steganography_indicators(self, text: str) -> Dict[str, any]:
        """Detect potential steganography indicators."""
        indicators = {}
        
        # Check for unusual whitespace patterns
        whitespace_pattern = r'[ \t]{2,}'
        whitespace_matches = re.findall(whitespace_pattern, text)
        if whitespace_matches:
            indicators['unusual_whitespace'] = {
                'count': len(whitespace_matches),
                'max_length': max(len(match) for match in whitespace_matches)
            }
        
        # Check for zero-width characters (already covered in core, but more detailed here)
        zero_width_chars = ['\u200B', '\u200C', '\u200D', '\u2060', '\uFEFF']
        zero_width_found = []
        for char in zero_width_chars:
            count = text.count(char)
            if count > 0:
                zero_width_found.append({'char': f"U+{ord(char):04X}", 'count': count})
        
        if zero_width_found:
            indicators['zero_width_chars'] = zero_width_found
        
        # Check for unusual Unicode normalization differences
        nfc_text = unicodedata.normalize('NFC', text)
        nfd_text = unicodedata.normalize('NFD', text)
        
        if len(nfc_text) != len(nfd_text):
            indicators['normalization_differences'] = {
                'nfc_length': len(nfc_text),
                'nfd_length': len(nfd_text),
                'difference': abs(len(nfc_text) - len(nfd_text))
            }
        
        return indicators
    
    def comprehensive_threat_analysis(self, text: str) -> Dict[str, any]:
        """Perform comprehensive threat analysis using all advanced detectors."""
        analysis = {
            'timestamp': str(datetime.now()),
            'text_length': len(text),
            'analysis_results': {}
        }
        
        # Run all detection algorithms
        analysis['analysis_results']['homoglyphs'] = self.detect_advanced_homoglyphs(text)
        analysis['analysis_results']['script_mixing'] = self.detect_script_mixing(text)
        analysis['analysis_results']['character_distribution'] = self.analyze_character_distribution(text)
        analysis['analysis_results']['adversarial_patterns'] = self.detect_adversarial_patterns(text)
        analysis['analysis_results']['entropy_distribution'] = self.analyze_entropy_distribution(text)
        analysis['analysis_results']['steganography'] = self.detect_steganography_indicators(text)
        
        # Calculate overall threat score
        threat_score = self._calculate_threat_score(analysis['analysis_results'])
        analysis['threat_score'] = threat_score
        analysis['threat_level'] = self._threat_score_to_level(threat_score)
        
        return analysis
    
    def _calculate_threat_score(self, results: Dict[str, any]) -> float:
        """Calculate overall threat score from analysis results."""
        score = 0.0
        
        # Homoglyph scoring
        if results['homoglyphs']:
            ratio = results['homoglyphs'].get('ratio', 0)
            score += min(ratio * 50, 20)  # Max 20 points
        
        # Script mixing scoring
        if results['script_mixing']:
            score += len(results['script_mixing']) * 10  # 10 points per suspicious mixing
        
        # Character distribution scoring
        if results['character_distribution'].get('outliers'):
            score += len(results['character_distribution']['outliers']) * 5
        
        # Adversarial patterns scoring
        if results['adversarial_patterns']:
            score += len(results['adversarial_patterns']) * 15
        
        # Entropy anomalies scoring
        entropy_analysis = results['entropy_distribution']
        if entropy_analysis.get('high_variance'):
            score += 10
        if entropy_analysis.get('very_low_entropy_regions'):
            score += 15
        if entropy_analysis.get('very_high_entropy_regions'):
            score += 10
        
        # Steganography indicators scoring
        if results['steganography']:
            score += len(results['steganography']) * 8
        
        return min(score, 100)  # Cap at 100
    
    def _threat_score_to_level(self, score: float) -> str:
        """Convert threat score to threat level."""
        if score < 10:
            return 'low'
        elif score < 30:
            return 'medium'
        elif score < 60:
            return 'high'
        else:
            return 'critical'
