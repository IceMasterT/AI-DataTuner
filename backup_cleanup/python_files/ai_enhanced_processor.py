#!/usr/bin/env python3
"""
AI-Enhanced Text Processor that combines rule-based and AI-powered approaches.
Provides the best of both worlds: speed of rules + intelligence of AI.
"""

import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from text_formatter import ConversationFormatter
from secure_text_processor import SecureTextProcessor
from ai_classifier import HybridTextClassifier, SmartClassificationPipeline
from content_enhancer import AIContentEnhancer, EnhancementType
from openai_integration import OpenAIConfig
from format_templates import ConversationFormat


@dataclass
class ProcessingConfig:
    """Configuration for AI-enhanced processing."""
    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    daily_cost_limit: float = 5.0
    
    # AI features
    enable_ai_classification: bool = True
    enable_content_enhancement: bool = False
    ai_confidence_threshold: float = 0.8
    
    # Enhancement settings
    auto_enhance_quality_threshold: float = 0.7
    enhancement_types: List[str] = None
    
    # Security settings
    enable_security_filtering: bool = True
    security_level: str = "balanced"
    
    # Performance settings
    enable_caching: bool = True
    cache_duration_hours: int = 24
    batch_size: int = 10
    
    def __post_init__(self):
        if self.enhancement_types is None:
            self.enhancement_types = ["grammar", "clarity"]


@dataclass
class ProcessingResult:
    """Result of AI-enhanced processing."""
    success: bool
    original_text: str
    processed_text: Optional[str]
    
    # Classification details
    classification_method: str
    classification_confidence: float
    
    # Enhancement details
    enhancement_applied: bool
    enhancement_types: List[str]
    quality_improvement: float
    
    # Cost and performance
    total_cost: float
    total_tokens: int
    processing_time: float
    cached_responses: int
    
    # Security
    security_threats: List[str]
    security_action: str
    
    # Errors and warnings
    errors: List[str]
    warnings: List[str]


class AIEnhancedTextProcessor:
    """Main AI-enhanced text processor."""
    
    def __init__(self, config: ProcessingConfig, output_format: str = "qwen"):
        self.config = config
        self.output_format = output_format
        
        # Initialize components
        self._init_components()
        
        # Statistics
        self.processing_stats = {
            'total_processed': 0,
            'ai_classifications': 0,
            'enhancements_applied': 0,
            'total_cost': 0.0,
            'total_tokens': 0,
            'cache_hits': 0,
            'security_blocks': 0
        }
    
    def _init_components(self):
        """Initialize all processing components."""
        # Security processor
        if self.config.enable_security_filtering:
            self.security_processor = SecureTextProcessor(
                output_format=self.config.security_level,
                aggressive_mode=(self.config.security_level in ["strict", "paranoid"])
            )
        else:
            self.security_processor = None
        
        # OpenAI configuration
        openai_config = None
        if self.config.enable_ai_classification or self.config.enable_content_enhancement:
            openai_config = OpenAIConfig(
                api_key=self.config.openai_api_key,
                model=self.config.openai_model,
                enable_caching=self.config.enable_caching,
                cache_duration_hours=self.config.cache_duration_hours,
                cost_limit_per_day=self.config.daily_cost_limit
            )
        
        # AI classifier
        if self.config.enable_ai_classification:
            self.classification_pipeline = SmartClassificationPipeline(openai_config)
        else:
            self.classification_pipeline = None
        
        # Content enhancer
        if self.config.enable_content_enhancement and openai_config:
            self.content_enhancer = AIContentEnhancer(openai_config)
        else:
            self.content_enhancer = None
        
        # Fallback formatter
        self.fallback_formatter = ConversationFormatter(self.output_format)
    
    def process_text(self, text: str, source_file: str = None) -> ProcessingResult:
        """
        Process text with full AI enhancement pipeline.
        
        Args:
            text: Input text to process
            source_file: Source file path for logging
            
        Returns:
            ProcessingResult with all processing details
        """
        start_time = time.time()
        
        result = ProcessingResult(
            success=False,
            original_text=text,
            processed_text=None,
            classification_method="none",
            classification_confidence=0.0,
            enhancement_applied=False,
            enhancement_types=[],
            quality_improvement=0.0,
            total_cost=0.0,
            total_tokens=0,
            processing_time=0.0,
            cached_responses=0,
            security_threats=[],
            security_action="none",
            errors=[],
            warnings=[]
        )
        
        try:
            # Step 1: Security filtering
            if self.security_processor:
                security_result = self.security_processor.process_text(text, source_file)
                
                if not security_result['success']:
                    result.security_threats = [t.get('threat_level', 'unknown') 
                                             for t in security_result.get('security_analysis', {}).values()]
                    result.security_action = security_result['action_taken']
                    result.errors.extend(security_result['errors'])
                    result.processing_time = time.time() - start_time
                    self.processing_stats['security_blocks'] += 1
                    return result
                
                # Use sanitized text
                text = security_result.get('processed_text', text)
                result.security_action = security_result['action_taken']
                if security_result['warnings']:
                    result.warnings.extend(security_result['warnings'])
            
            # Step 2: Content enhancement (if enabled and needed)
            enhanced_text = text
            if self.content_enhancer:
                enhancement_result = self._apply_content_enhancement(text)
                if enhancement_result:
                    enhanced_text = enhancement_result.enhanced_text
                    result.enhancement_applied = True
                    result.enhancement_types = [enhancement_result.enhancement_type.value]
                    result.quality_improvement = (enhancement_result.quality_score_after - 
                                                enhancement_result.quality_score_before)
                    result.total_cost += enhancement_result.cost
                    result.total_tokens += enhancement_result.tokens_used
                    if enhancement_result.cached:
                        result.cached_responses += 1
                    
                    self.processing_stats['enhancements_applied'] += 1
            
            # Step 3: Text segmentation and classification
            if self.classification_pipeline:
                # Use AI-enhanced classification
                segments = self._segment_text(enhanced_text)
                classified_segments = self.classification_pipeline.process_conversation_segments(segments)
                
                # Get classification stats
                classification_stats = self.classification_pipeline.get_processing_report()
                if 'recent_stats' in classification_stats:
                    recent_stats = classification_stats['recent_stats']
                    result.classification_method = "ai_enhanced"
                    result.classification_confidence = recent_stats.get('average_confidence', 0.0)
                    result.total_cost += recent_stats.get('total_cost', 0.0)
                    result.total_tokens += recent_stats.get('total_tokens', 0)
                    result.cached_responses += recent_stats.get('cached_responses', 0)
                    
                    self.processing_stats['ai_classifications'] += 1
            else:
                # Use fallback rule-based classification
                segments = self._segment_text(enhanced_text)
                classified_segments = [(self._classify_segment(seg), seg) for seg in segments]
                result.classification_method = "rule_based"
                result.classification_confidence = 0.7  # Estimated
            
            # Step 4: Format output
            formatted_text = self._format_conversation(classified_segments)
            
            # Success!
            result.success = True
            result.processed_text = formatted_text
            result.processing_time = time.time() - start_time
            
            # Update statistics
            self._update_stats(result)
            
        except Exception as e:
            result.errors.append(f"Processing error: {str(e)}")
            result.processing_time = time.time() - start_time
        
        return result
    
    def _apply_content_enhancement(self, text: str) -> Optional[Any]:
        """Apply content enhancement if needed."""
        # Get enhancement suggestions
        suggestions = self.content_enhancer.get_enhancement_suggestions(text)
        
        # Check if enhancement is needed
        if suggestions['overall_quality'] >= self.config.auto_enhance_quality_threshold:
            return None  # Text is already good quality
        
        # Apply most needed enhancement
        priority_suggestions = [s for s in suggestions['suggestions'] if s['priority'] == 'high']
        if not priority_suggestions:
            priority_suggestions = suggestions['suggestions']
        
        if priority_suggestions:
            enhancement_type_str = priority_suggestions[0]['type']
            enhancement_type = EnhancementType(enhancement_type_str)
            return self.content_enhancer.enhance_content(text, enhancement_type)
        
        return None
    
    def _segment_text(self, text: str) -> List[str]:
        """Segment text into logical parts."""
        # Use the existing segmentation logic
        from utils import split_text_intelligently, preprocess_text
        return split_text_intelligently(preprocess_text(text))
    
    def _classify_segment(self, segment: str) -> str:
        """Fallback rule-based classification."""
        from utils import score_as_question, score_as_answer
        
        question_score = score_as_question(segment)
        answer_score = score_as_answer(segment)
        
        return "user" if question_score > answer_score else "assistant"
    
    def _format_conversation(self, classified_segments: List[Tuple[str, str]]) -> str:
        """Format classified segments into conversation format."""
        # Use the existing formatter
        from format_templates import FormatFactory
        
        try:
            format_enum = ConversationFormat(self.output_format)
            template = FormatFactory.create_template(format_enum)
            return template.format_conversation(classified_segments)
        except Exception:
            # Fallback formatting
            lines = []
            for role, content in classified_segments:
                lines.append(f"<|{role}|> {content}")
            return "\n\n".join(lines)
    
    def _update_stats(self, result: ProcessingResult):
        """Update processing statistics."""
        self.processing_stats['total_processed'] += 1
        self.processing_stats['total_cost'] += result.total_cost
        self.processing_stats['total_tokens'] += result.total_tokens
        self.processing_stats['cache_hits'] += result.cached_responses
    
    def batch_process(self, texts: List[str], source_files: List[str] = None) -> List[ProcessingResult]:
        """Process multiple texts efficiently."""
        if source_files is None:
            source_files = [None] * len(texts)
        
        results = []
        
        # Process in batches to manage memory and costs
        batch_size = self.config.batch_size
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_files = source_files[i:i + batch_size]
            
            batch_results = []
            for text, source_file in zip(batch_texts, batch_files):
                result = self.process_text(text, source_file)
                batch_results.append(result)
            
            results.extend(batch_results)
            
            # Check cost limits
            if self.processing_stats['total_cost'] >= self.config.daily_cost_limit:
                remaining_results = [
                    ProcessingResult(
                        success=False,
                        original_text=text,
                        processed_text=None,
                        classification_method="none",
                        classification_confidence=0.0,
                        enhancement_applied=False,
                        enhancement_types=[],
                        quality_improvement=0.0,
                        total_cost=0.0,
                        total_tokens=0,
                        processing_time=0.0,
                        cached_responses=0,
                        security_threats=[],
                        security_action="none",
                        errors=["Daily cost limit reached"],
                        warnings=[]
                    )
                    for text in texts[i + batch_size:]
                ]
                results.extend(remaining_results)
                break
        
        return results
    
    def get_processing_report(self) -> Dict[str, Any]:
        """Get comprehensive processing report."""
        report = {
            'processing_statistics': self.processing_stats.copy(),
            'configuration': {
                'ai_classification_enabled': self.config.enable_ai_classification,
                'content_enhancement_enabled': self.config.enable_content_enhancement,
                'security_filtering_enabled': self.config.enable_security_filtering,
                'output_format': self.output_format,
                'model': self.config.openai_model
            },
            'performance_metrics': {
                'avg_cost_per_item': (self.processing_stats['total_cost'] / 
                                     max(1, self.processing_stats['total_processed'])),
                'cache_hit_rate': (self.processing_stats['cache_hits'] / 
                                  max(1, self.processing_stats['total_processed'])),
                'ai_usage_rate': (self.processing_stats['ai_classifications'] / 
                                 max(1, self.processing_stats['total_processed'])),
                'enhancement_rate': (self.processing_stats['enhancements_applied'] / 
                                    max(1, self.processing_stats['total_processed']))
            }
        }
        
        # Add AI-specific reports if available
        if self.classification_pipeline:
            ai_report = self.classification_pipeline.get_processing_report()
            report['ai_classification_report'] = ai_report
        
        return report
    
    def optimize_for_cost(self):
        """Optimize settings for cost efficiency."""
        self.config.enable_content_enhancement = False
        self.config.ai_confidence_threshold = 0.9
        self.config.auto_enhance_quality_threshold = 0.9
        
        if self.classification_pipeline:
            self.classification_pipeline.optimize_for_cost()
    
    def optimize_for_quality(self):
        """Optimize settings for maximum quality."""
        self.config.enable_content_enhancement = True
        self.config.ai_confidence_threshold = 0.6
        self.config.auto_enhance_quality_threshold = 0.6
        
        if self.classification_pipeline:
            self.classification_pipeline.optimize_for_accuracy()
    
    def get_cost_estimate(self, text_length: int, num_texts: int = 1) -> Dict[str, float]:
        """Estimate processing costs."""
        from openai_integration import TokenCounter
        
        # Estimate tokens
        estimated_tokens = TokenCounter.estimate_tokens(text_length * num_texts)
        
        # Estimate costs for different operations
        classification_cost = 0.0
        enhancement_cost = 0.0
        
        if self.config.enable_ai_classification:
            classification_cost = TokenCounter.estimate_cost(
                self.config.openai_model, estimated_tokens, estimated_tokens // 4
            ) * num_texts
        
        if self.config.enable_content_enhancement:
            enhancement_cost = TokenCounter.estimate_cost(
                self.config.openai_model, estimated_tokens, estimated_tokens
            ) * num_texts * 0.5  # Assume 50% need enhancement
        
        total_cost = classification_cost + enhancement_cost
        
        return {
            'classification_cost': classification_cost,
            'enhancement_cost': enhancement_cost,
            'total_estimated_cost': total_cost,
            'estimated_tokens': estimated_tokens,
            'within_daily_limit': total_cost <= self.config.daily_cost_limit
        }
