#!/usr/bin/env python3
"""
AI-powered content enhancement for improving text quality and clarity.
Provides grammar correction, clarity improvement, and content completion.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from openai_integration import OpenAIClient, OpenAIConfig


class EnhancementType(Enum):
    """Types of content enhancement."""
    GRAMMAR = "grammar"
    CLARITY = "clarity"
    STRUCTURE = "structure"
    COMPLETENESS = "completeness"
    CONCISENESS = "conciseness"
    FORMALITY = "formality"
    TECHNICAL_ACCURACY = "technical_accuracy"


@dataclass
class EnhancementResult:
    """Result of content enhancement."""
    original_text: str
    enhanced_text: str
    enhancement_type: EnhancementType
    improvements_made: List[str]
    quality_score_before: float
    quality_score_after: float
    tokens_used: int = 0
    cost: float = 0.0
    cached: bool = False
    processing_time: float = 0.0


class ContentQualityAnalyzer:
    """Analyze text quality using various metrics."""
    
    @staticmethod
    def analyze_text_quality(text: str) -> Dict[str, float]:
        """Analyze text quality across multiple dimensions."""
        metrics = {}
        
        # Basic metrics
        word_count = len(text.split())
        sentence_count = len(re.findall(r'[.!?]+', text))
        
        # Grammar indicators
        metrics['grammar_score'] = ContentQualityAnalyzer._estimate_grammar_quality(text)
        
        # Clarity indicators
        metrics['clarity_score'] = ContentQualityAnalyzer._estimate_clarity(text, word_count, sentence_count)
        
        # Completeness indicators
        metrics['completeness_score'] = ContentQualityAnalyzer._estimate_completeness(text)
        
        # Structure indicators
        metrics['structure_score'] = ContentQualityAnalyzer._estimate_structure(text)
        
        # Overall quality (weighted average)
        metrics['overall_quality'] = (
            metrics['grammar_score'] * 0.3 +
            metrics['clarity_score'] * 0.3 +
            metrics['completeness_score'] * 0.2 +
            metrics['structure_score'] * 0.2
        )
        
        return metrics
    
    @staticmethod
    def _estimate_grammar_quality(text: str) -> float:
        """Estimate grammar quality based on simple heuristics."""
        score = 1.0
        
        # Check for common grammar issues
        issues = 0
        
        # Double spaces
        if '  ' in text:
            issues += text.count('  ')
        
        # Missing capitalization after periods
        if re.search(r'\. [a-z]', text):
            issues += len(re.findall(r'\. [a-z]', text))
        
        # Missing spaces after punctuation
        if re.search(r'[.!?][A-Za-z]', text):
            issues += len(re.findall(r'[.!?][A-Za-z]', text))
        
        # Excessive punctuation
        if re.search(r'[.!?]{3,}', text):
            issues += len(re.findall(r'[.!?]{3,}', text))
        
        # Penalize based on issues
        penalty = min(0.8, issues * 0.1)
        return max(0.1, score - penalty)
    
    @staticmethod
    def _estimate_clarity(text: str, word_count: int, sentence_count: int) -> float:
        """Estimate text clarity."""
        if sentence_count == 0:
            return 0.1
        
        # Average words per sentence
        avg_words_per_sentence = word_count / sentence_count
        
        # Optimal range is 15-20 words per sentence
        if 15 <= avg_words_per_sentence <= 20:
            length_score = 1.0
        elif avg_words_per_sentence < 10:
            length_score = 0.7  # Too short, might be choppy
        elif avg_words_per_sentence > 30:
            length_score = 0.5  # Too long, might be confusing
        else:
            length_score = 0.8
        
        # Check for transition words
        transition_words = ['however', 'therefore', 'furthermore', 'moreover', 'additionally', 'consequently']
        has_transitions = any(word in text.lower() for word in transition_words)
        transition_score = 1.0 if has_transitions else 0.8
        
        # Check for varied sentence structure
        sentences = re.split(r'[.!?]+', text)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        
        if len(sentence_lengths) > 1:
            length_variance = max(sentence_lengths) - min(sentence_lengths)
            variety_score = min(1.0, length_variance / 10)  # Normalize
        else:
            variety_score = 0.5
        
        return (length_score * 0.5 + transition_score * 0.3 + variety_score * 0.2)
    
    @staticmethod
    def _estimate_completeness(text: str) -> float:
        """Estimate content completeness."""
        # Check for incomplete sentences
        incomplete_indicators = ['...', 'etc.', 'and so on', 'among others']
        has_incomplete = any(indicator in text.lower() for indicator in incomplete_indicators)
        
        # Check for questions without answers
        questions = text.count('?')
        statements = len(re.findall(r'[.!]', text))
        
        if questions > 0 and statements == 0:
            return 0.3  # Only questions, no answers
        
        # Check minimum length
        word_count = len(text.split())
        if word_count < 10:
            return 0.4  # Too short to be complete
        
        completeness_score = 0.9 if not has_incomplete else 0.6
        return completeness_score
    
    @staticmethod
    def _estimate_structure(text: str) -> float:
        """Estimate text structure quality."""
        # Check for proper paragraph structure
        paragraphs = text.split('\n\n')
        
        # Single paragraph gets lower score
        if len(paragraphs) == 1 and len(text.split()) > 50:
            paragraph_score = 0.6
        else:
            paragraph_score = 1.0
        
        # Check for logical flow indicators
        flow_indicators = ['first', 'second', 'finally', 'in conclusion', 'to summarize']
        has_flow = any(indicator in text.lower() for indicator in flow_indicators)
        flow_score = 1.0 if has_flow else 0.8
        
        return (paragraph_score * 0.6 + flow_score * 0.4)


class AIContentEnhancer:
    """AI-powered content enhancement system."""
    
    def __init__(self, openai_config: OpenAIConfig):
        self.ai_client = OpenAIClient(openai_config)
        self.quality_analyzer = ContentQualityAnalyzer()
    
    def enhance_content(self, text: str, enhancement_type: EnhancementType,
                       preserve_meaning: bool = True) -> EnhancementResult:
        """
        Enhance content using AI.
        
        Args:
            text: Original text to enhance
            enhancement_type: Type of enhancement to apply
            preserve_meaning: Whether to strictly preserve original meaning
            
        Returns:
            EnhancementResult with enhanced text and metadata
        """
        import time
        start_time = time.time()
        
        # Analyze original quality
        original_quality = self.quality_analyzer.analyze_text_quality(text)
        
        # Get enhancement prompt
        system_prompt = self._get_enhancement_prompt(enhancement_type, preserve_meaning)
        
        try:
            # Enhance with AI
            ai_result = self.ai_client.enhance_content(text, enhancement_type.value)
            enhanced_text = ai_result["enhanced_text"]
            
            # Analyze enhanced quality
            enhanced_quality = self.quality_analyzer.analyze_text_quality(enhanced_text)
            
            # Identify improvements
            improvements = self._identify_improvements(text, enhanced_text, enhancement_type)
            
            processing_time = time.time() - start_time
            
            return EnhancementResult(
                original_text=text,
                enhanced_text=enhanced_text,
                enhancement_type=enhancement_type,
                improvements_made=improvements,
                quality_score_before=original_quality['overall_quality'],
                quality_score_after=enhanced_quality['overall_quality'],
                tokens_used=ai_result["tokens_used"],
                cost=ai_result["cost"],
                cached=ai_result["cached"],
                processing_time=processing_time
            )
            
        except Exception as e:
            # Return original text on error
            return EnhancementResult(
                original_text=text,
                enhanced_text=text,
                enhancement_type=enhancement_type,
                improvements_made=[f"Enhancement failed: {str(e)}"],
                quality_score_before=original_quality['overall_quality'],
                quality_score_after=original_quality['overall_quality'],
                processing_time=time.time() - start_time
            )
    
    def _get_enhancement_prompt(self, enhancement_type: EnhancementType, 
                               preserve_meaning: bool) -> str:
        """Get system prompt for specific enhancement type."""
        base_instruction = "You are a professional text editor. "
        preservation_note = "Preserve the original meaning exactly. " if preserve_meaning else ""
        
        prompts = {
            EnhancementType.GRAMMAR: f"{base_instruction}{preservation_note}Fix grammar, spelling, and punctuation errors while maintaining the original style and tone.",
            
            EnhancementType.CLARITY: f"{base_instruction}{preservation_note}Improve clarity and readability. Make complex sentences easier to understand, clarify ambiguous phrases, and ensure logical flow.",
            
            EnhancementType.STRUCTURE: f"{base_instruction}{preservation_note}Improve text structure and organization. Ensure logical paragraph breaks, smooth transitions, and coherent flow of ideas.",
            
            EnhancementType.COMPLETENESS: f"{base_instruction}{preservation_note}If the text appears incomplete or lacks important context, suggest improvements. Add necessary details while maintaining accuracy.",
            
            EnhancementType.CONCISENESS: f"{base_instruction}{preservation_note}Make the text more concise by removing redundancy and unnecessary words while preserving all important information.",
            
            EnhancementType.FORMALITY: f"{base_instruction}{preservation_note}Adjust the tone to be more formal and professional while maintaining clarity and readability.",
            
            EnhancementType.TECHNICAL_ACCURACY: f"{base_instruction}{preservation_note}Improve technical accuracy and precision. Ensure proper use of terminology and clear explanations of technical concepts."
        }
        
        return prompts.get(enhancement_type, prompts[EnhancementType.CLARITY])
    
    def _identify_improvements(self, original: str, enhanced: str, 
                              enhancement_type: EnhancementType) -> List[str]:
        """Identify specific improvements made."""
        improvements = []
        
        # Length changes
        orig_words = len(original.split())
        enh_words = len(enhanced.split())
        
        if enh_words > orig_words * 1.1:
            improvements.append(f"Expanded content (+{enh_words - orig_words} words)")
        elif enh_words < orig_words * 0.9:
            improvements.append(f"Made more concise (-{orig_words - enh_words} words)")
        
        # Grammar improvements
        if enhancement_type == EnhancementType.GRAMMAR:
            # Check for common fixes
            if original.count('  ') > enhanced.count('  '):
                improvements.append("Fixed spacing issues")
            
            if len(re.findall(r'\. [a-z]', original)) > len(re.findall(r'\. [a-z]', enhanced)):
                improvements.append("Fixed capitalization")
        
        # Structure improvements
        if enhancement_type == EnhancementType.STRUCTURE:
            orig_paragraphs = len(original.split('\n\n'))
            enh_paragraphs = len(enhanced.split('\n\n'))
            
            if enh_paragraphs > orig_paragraphs:
                improvements.append("Improved paragraph structure")
        
        # Clarity improvements
        if enhancement_type == EnhancementType.CLARITY:
            # Check for transition words added
            transition_words = ['however', 'therefore', 'furthermore', 'moreover']
            orig_transitions = sum(1 for word in transition_words if word in original.lower())
            enh_transitions = sum(1 for word in transition_words if word in enhanced.lower())
            
            if enh_transitions > orig_transitions:
                improvements.append("Added transition words for better flow")
        
        # Generic improvement if none specific found
        if not improvements:
            improvements.append(f"Applied {enhancement_type.value} enhancement")
        
        return improvements
    
    def batch_enhance(self, texts: List[str], enhancement_type: EnhancementType) -> List[EnhancementResult]:
        """Enhance multiple texts efficiently."""
        results = []
        
        for text in texts:
            result = self.enhance_content(text, enhancement_type)
            results.append(result)
        
        return results
    
    def auto_enhance(self, text: str, quality_threshold: float = 0.7) -> EnhancementResult:
        """Automatically determine and apply the best enhancement."""
        # Analyze current quality
        quality_metrics = self.quality_analyzer.analyze_text_quality(text)
        
        # Determine what needs improvement most
        if quality_metrics['grammar_score'] < quality_threshold:
            enhancement_type = EnhancementType.GRAMMAR
        elif quality_metrics['clarity_score'] < quality_threshold:
            enhancement_type = EnhancementType.CLARITY
        elif quality_metrics['structure_score'] < quality_threshold:
            enhancement_type = EnhancementType.STRUCTURE
        elif quality_metrics['completeness_score'] < quality_threshold:
            enhancement_type = EnhancementType.COMPLETENESS
        else:
            # Text is already good, apply general clarity enhancement
            enhancement_type = EnhancementType.CLARITY
        
        return self.enhance_content(text, enhancement_type)
    
    def get_enhancement_suggestions(self, text: str) -> Dict[str, Any]:
        """Get suggestions for potential enhancements."""
        quality_metrics = self.quality_analyzer.analyze_text_quality(text)
        suggestions = []
        
        threshold = 0.7
        
        if quality_metrics['grammar_score'] < threshold:
            suggestions.append({
                'type': 'grammar',
                'priority': 'high',
                'description': 'Text has grammar or spelling issues',
                'current_score': quality_metrics['grammar_score']
            })
        
        if quality_metrics['clarity_score'] < threshold:
            suggestions.append({
                'type': 'clarity',
                'priority': 'medium',
                'description': 'Text could be clearer and more readable',
                'current_score': quality_metrics['clarity_score']
            })
        
        if quality_metrics['structure_score'] < threshold:
            suggestions.append({
                'type': 'structure',
                'priority': 'medium',
                'description': 'Text structure could be improved',
                'current_score': quality_metrics['structure_score']
            })
        
        if quality_metrics['completeness_score'] < threshold:
            suggestions.append({
                'type': 'completeness',
                'priority': 'low',
                'description': 'Text might be incomplete or lack context',
                'current_score': quality_metrics['completeness_score']
            })
        
        return {
            'overall_quality': quality_metrics['overall_quality'],
            'suggestions': suggestions,
            'quality_breakdown': quality_metrics
        }
