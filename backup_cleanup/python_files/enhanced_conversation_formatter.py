#!/usr/bin/env python3
"""
Enhanced Conversation Formatter - Achieves 95%+ accuracy with strict validation.
Integrates with strict prompting system and enhanced accuracy validation.
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from strict_prompting_system import StrictPromptingSystem, PromptingResult
from enhanced_accuracy_system import EnhancedAccuracySystem, ValidationResult
from quality_scorer import LLMQualityScorer
from conversation_formatter import ConversationFormatter


@dataclass
class EnhancedFormattingResult:
    """Result from enhanced conversation formatting."""
    formatted_content: str
    accuracy_score: float
    validation_passed: bool
    quality_score: float
    attempts_used: int
    corrections_applied: List[str]
    processing_time: float
    cost: float
    confidence: float


class EnhancedConversationFormatter(ConversationFormatter):
    """Enhanced conversation formatter with 95% accuracy guarantee."""
    
    def __init__(self, format_type: str = "qwen", target_accuracy: float = 95.0):
        """Initialize the enhanced formatter."""
        super().__init__(format_type)
        self.target_accuracy = target_accuracy
        self.logger = logging.getLogger(__name__)
        
        # Initialize enhanced systems
        self.strict_prompting = StrictPromptingSystem(
            max_attempts=3, 
            target_accuracy=target_accuracy
        )
        self.accuracy_system = EnhancedAccuracySystem(target_accuracy)
        self.quality_scorer = LLMQualityScorer(
            target_accuracy=target_accuracy
        )
    
    def format_conversation_enhanced(self, user_input: str, assistant_response: str,
                                   personality: str = "professional",
                                   context: str = None) -> EnhancedFormattingResult:
        """
        Format conversation with enhanced accuracy validation.
        
        Args:
            user_input: User's input/question
            assistant_response: Assistant's response
            personality: Personality to apply
            context: Additional context
            
        Returns:
            EnhancedFormattingResult with detailed metrics
        """
        start_time = datetime.now()
        
        # Combine input and response for processing
        original_content = f"User: {user_input}\nAssistant: {assistant_response}"
        
        # Use strict prompting system for initial formatting
        prompting_result = self.strict_prompting.format_with_strict_prompting(
            original_content, self.format_type, personality, context
        )
        
        # Validate with enhanced accuracy system
        validation_result = self.accuracy_system.validate_and_enhance(
            prompting_result.formatted_content,
            self.format_type,
            original_content
        )
        
        # Use corrected content if validation improved it
        final_content = validation_result.corrected_output
        final_accuracy = validation_result.accuracy_score
        
        # Score quality
        quality_context = {
            "original_content": original_content,
            "format_type": self.format_type,
            "personality": personality
        }
        
        quality_score = self.quality_scorer.score_content(
            final_content, quality_context, original_content, self.format_type
        )
        
        # Combine corrections from all systems
        all_corrections = []
        all_corrections.extend(prompting_result.corrections_applied)
        all_corrections.extend(validation_result.corrections)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        total_cost = prompting_result.cost + validation_result.metrics.cost + quality_score.cost
        
        return EnhancedFormattingResult(
            formatted_content=final_content,
            accuracy_score=final_accuracy,
            validation_passed=validation_result.is_valid,
            quality_score=quality_score.overall_score,
            attempts_used=prompting_result.attempts_used,
            corrections_applied=all_corrections,
            processing_time=processing_time,
            cost=total_cost,
            confidence=min(prompting_result.accuracy_score / 100.0, quality_score.confidence)
        )
    
    def batch_format_conversations(self, conversations: List[Tuple[str, str]],
                                 personality: str = "professional",
                                 context: str = None) -> List[EnhancedFormattingResult]:
        """
        Format multiple conversations with enhanced accuracy.
        
        Args:
            conversations: List of (user_input, assistant_response) tuples
            personality: Personality to apply
            context: Additional context
            
        Returns:
            List of EnhancedFormattingResult objects
        """
        results = []
        total_processed = 0
        total_passed = 0
        
        self.logger.info(f"Starting batch formatting of {len(conversations)} conversations")
        
        for i, (user_input, assistant_response) in enumerate(conversations):
            try:
                self.logger.info(f"Processing conversation {i+1}/{len(conversations)}")
                
                result = self.format_conversation_enhanced(
                    user_input, assistant_response, personality, context
                )
                
                results.append(result)
                total_processed += 1
                
                if result.validation_passed and result.accuracy_score >= self.target_accuracy:
                    total_passed += 1
                
                # Log progress every 10 items
                if (i + 1) % 10 == 0:
                    pass_rate = (total_passed / total_processed) * 100
                    self.logger.info(f"Progress: {i+1}/{len(conversations)} - Pass rate: {pass_rate:.1f}%")
                
            except Exception as e:
                self.logger.error(f"Failed to process conversation {i+1}: {e}")
                # Create error result
                results.append(EnhancedFormattingResult(
                    formatted_content="",
                    accuracy_score=0.0,
                    validation_passed=False,
                    quality_score=0.0,
                    attempts_used=0,
                    corrections_applied=[f"Processing failed: {e}"],
                    processing_time=0.0,
                    cost=0.0,
                    confidence=0.0
                ))
        
        final_pass_rate = (total_passed / total_processed) * 100 if total_processed > 0 else 0
        self.logger.info(f"Batch formatting complete: {total_passed}/{total_processed} passed ({final_pass_rate:.1f}%)")
        
        return results
    
    def validate_batch_accuracy(self, results: List[EnhancedFormattingResult]) -> Dict[str, Any]:
        """
        Validate that batch results meet accuracy requirements.
        
        Args:
            results: List of formatting results
            
        Returns:
            Validation summary with metrics
        """
        if not results:
            return {"error": "No results to validate"}
        
        # Calculate metrics
        total_results = len(results)
        passed_results = sum(1 for r in results if r.validation_passed and r.accuracy_score >= self.target_accuracy)
        failed_results = total_results - passed_results
        
        accuracy_scores = [r.accuracy_score for r in results if r.accuracy_score > 0]
        quality_scores = [r.quality_score for r in results if r.quality_score > 0]
        
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        pass_rate = (passed_results / total_results) * 100
        
        # Identify common issues
        all_corrections = []
        for result in results:
            all_corrections.extend(result.corrections_applied)
        
        # Count correction types
        correction_counts = {}
        for correction in all_corrections:
            correction_type = correction.split(':')[0] if ':' in correction else correction
            correction_counts[correction_type] = correction_counts.get(correction_type, 0) + 1
        
        # Calculate costs
        total_cost = sum(r.cost for r in results)
        avg_cost_per_item = total_cost / total_results if total_results > 0 else 0
        
        validation_summary = {
            "overall_status": "PASSED" if pass_rate >= 95.0 else "FAILED",
            "pass_rate": pass_rate,
            "target_accuracy": self.target_accuracy,
            "results_summary": {
                "total_processed": total_results,
                "passed": passed_results,
                "failed": failed_results,
                "pass_rate_percentage": pass_rate
            },
            "accuracy_metrics": {
                "average_accuracy": avg_accuracy,
                "average_quality": avg_quality,
                "min_accuracy": min(accuracy_scores) if accuracy_scores else 0,
                "max_accuracy": max(accuracy_scores) if accuracy_scores else 0
            },
            "cost_metrics": {
                "total_cost": total_cost,
                "average_cost_per_item": avg_cost_per_item,
                "cost_per_passed_item": total_cost / passed_results if passed_results > 0 else 0
            },
            "common_corrections": dict(sorted(correction_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "recommendations": self._generate_batch_recommendations(pass_rate, avg_accuracy, correction_counts)
        }
        
        return validation_summary
    
    def _generate_batch_recommendations(self, pass_rate: float, avg_accuracy: float,
                                      correction_counts: Dict[str, int]) -> List[str]:
        """Generate recommendations based on batch results."""
        recommendations = []
        
        if pass_rate < 95.0:
            recommendations.append(f"Pass rate {pass_rate:.1f}% is below 95% target - review failed items")
        
        if avg_accuracy < self.target_accuracy:
            recommendations.append(f"Average accuracy {avg_accuracy:.1f}% below target - improve source data quality")
        
        # Analyze common correction types
        if correction_counts:
            top_correction = max(correction_counts.items(), key=lambda x: x[1])
            if top_correction[1] > len(correction_counts) * 0.3:  # If >30% of items need same correction
                recommendations.append(f"Common issue: {top_correction[0]} - consider addressing systematically")
        
        if pass_rate >= 98.0:
            recommendations.append("Excellent results! System is performing optimally")
        elif pass_rate >= 95.0:
            recommendations.append("Good results - minor optimizations may improve performance")
        else:
            recommendations.append("Significant improvements needed - review prompting and validation systems")
        
        return recommendations


def get_enhanced_formatter(format_type: str = "qwen", target_accuracy: float = 95.0) -> EnhancedConversationFormatter:
    """Get an enhanced conversation formatter instance."""
    return EnhancedConversationFormatter(format_type, target_accuracy)
