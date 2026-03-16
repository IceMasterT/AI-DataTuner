#!/usr/bin/env python3
"""
AI-powered text classification using OpenAI for enhanced accuracy.
Combines rule-based and AI-powered approaches for optimal results.
"""

import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from openai_integration import OpenAIClient, OpenAIConfig
from text_formatter import AdvancedTextClassifier
from utils import score_as_question, score_as_answer


@dataclass
class ClassificationResult:
    """Result of AI-powered classification."""
    classification: str  # "user" or "assistant"
    confidence: float
    method: str  # "rule_based", "ai_powered", "hybrid"
    reasoning: str
    tokens_used: int = 0
    cost: float = 0.0
    cached: bool = False


class HybridTextClassifier:
    """Hybrid classifier combining rule-based and AI-powered approaches."""
    
    def __init__(self, openai_config: Optional[OpenAIConfig] = None, 
                 use_ai_fallback: bool = True, confidence_threshold: float = 0.8):
        """
        Initialize hybrid classifier.
        
        Args:
            openai_config: OpenAI configuration (None to disable AI)
            use_ai_fallback: Use AI when rule-based confidence is low
            confidence_threshold: Threshold for using rule-based results
        """
        self.rule_based_classifier = AdvancedTextClassifier()
        self.confidence_threshold = confidence_threshold
        self.use_ai_fallback = use_ai_fallback
        
        # Initialize OpenAI client if config provided
        self.ai_client = None
        if openai_config:
            try:
                self.ai_client = OpenAIClient(openai_config)
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI client: {e}")
                self.ai_client = None
    
    def classify_text(self, text: str, context: List[str] = None) -> ClassificationResult:
        """
        Classify text using hybrid approach.
        
        Args:
            text: Text to classify
            context: Previous text segments for context
            
        Returns:
            ClassificationResult with classification and metadata
        """
        # Step 1: Rule-based classification
        rule_based_result = self._rule_based_classify(text, context)
        
        # Step 2: Decide if AI enhancement is needed
        if (self.ai_client and 
            self.use_ai_fallback and 
            rule_based_result.confidence < self.confidence_threshold):
            
            # Use AI for better classification
            ai_result = self._ai_classify(text, context)
            
            # Combine results
            return self._combine_results(rule_based_result, ai_result, text)
        
        return rule_based_result
    
    def _rule_based_classify(self, text: str, context: List[str] = None) -> ClassificationResult:
        """Perform rule-based classification."""
        # Use existing rule-based classifier
        classification = self.rule_based_classifier.classify_text(text, context)
        
        # Calculate confidence based on scoring
        question_score = score_as_question(text)
        answer_score = score_as_answer(text)
        
        # Determine confidence
        score_diff = abs(question_score - answer_score)
        confidence = min(0.95, max(0.1, score_diff))
        
        # Generate reasoning
        reasoning = self._generate_rule_reasoning(text, question_score, answer_score)
        
        return ClassificationResult(
            classification=classification,
            confidence=confidence,
            method="rule_based",
            reasoning=reasoning
        )
    
    def _ai_classify(self, text: str, context: List[str] = None) -> ClassificationResult:
        """Perform AI-powered classification."""
        try:
            # Prepare context information
            context_info = ""
            if context:
                recent_context = context[-3:]  # Last 3 segments
                context_info = f"\n\nContext (previous segments): {' | '.join(recent_context)}"
            
            # Enhanced prompt with context
            enhanced_text = text + context_info
            
            # Get AI classification
            ai_result = self.ai_client.classify_text(enhanced_text)
            
            # Convert to our format
            classification = "user" if ai_result["classification"] == "question" else "assistant"
            
            return ClassificationResult(
                classification=classification,
                confidence=ai_result["confidence"],
                method="ai_powered",
                reasoning=ai_result["reasoning"],
                tokens_used=ai_result["tokens_used"],
                cost=ai_result["cost"],
                cached=ai_result["cached"]
            )
            
        except Exception as e:
            # Fallback to rule-based on AI failure
            return ClassificationResult(
                classification="assistant",  # Safe default
                confidence=0.1,
                method="ai_fallback_error",
                reasoning=f"AI classification failed: {str(e)}"
            )
    
    def _combine_results(self, rule_result: ClassificationResult, 
                        ai_result: ClassificationResult, text: str) -> ClassificationResult:
        """Combine rule-based and AI results intelligently."""
        
        # If AI has high confidence, prefer it
        if ai_result.confidence > 0.8:
            ai_result.method = "hybrid_ai_preferred"
            return ai_result
        
        # If rule-based has reasonable confidence, use it
        if rule_result.confidence > 0.6:
            rule_result.method = "hybrid_rule_preferred"
            return rule_result
        
        # Both have low confidence - use weighted average
        ai_weight = 0.7  # Prefer AI slightly when both are uncertain
        rule_weight = 0.3
        
        # Combine confidences
        combined_confidence = (ai_result.confidence * ai_weight + 
                             rule_result.confidence * rule_weight)
        
        # Choose classification based on higher individual confidence
        if ai_result.confidence > rule_result.confidence:
            final_classification = ai_result.classification
            primary_reasoning = ai_result.reasoning
        else:
            final_classification = rule_result.classification
            primary_reasoning = rule_result.reasoning
        
        combined_reasoning = (f"Hybrid: {primary_reasoning} "
                            f"(AI: {ai_result.confidence:.2f}, Rule: {rule_result.confidence:.2f})")
        
        return ClassificationResult(
            classification=final_classification,
            confidence=combined_confidence,
            method="hybrid_combined",
            reasoning=combined_reasoning,
            tokens_used=ai_result.tokens_used,
            cost=ai_result.cost,
            cached=ai_result.cached
        )
    
    def _generate_rule_reasoning(self, text: str, question_score: float, 
                               answer_score: float) -> str:
        """Generate reasoning for rule-based classification."""
        reasons = []
        
        if text.strip().endswith('?'):
            reasons.append("ends with question mark")
        
        if any(text.lower().startswith(word) for word in ['what', 'how', 'why', 'when', 'where', 'who']):
            reasons.append("starts with question word")
        
        if question_score > answer_score:
            reasons.append(f"question patterns (score: {question_score:.2f})")
        else:
            reasons.append(f"answer patterns (score: {answer_score:.2f})")
        
        return "Rule-based: " + ", ".join(reasons)
    
    def batch_classify(self, texts: List[str], context_per_text: List[List[str]] = None) -> List[ClassificationResult]:
        """Classify multiple texts efficiently."""
        results = []
        
        # Prepare context
        if context_per_text is None:
            context_per_text = [None] * len(texts)
        
        for i, text in enumerate(texts):
            context = context_per_text[i] if i < len(context_per_text) else None
            result = self.classify_text(text, context)
            results.append(result)
        
        return results
    
    def get_classification_stats(self, results: List[ClassificationResult]) -> Dict[str, Any]:
        """Get statistics from classification results."""
        if not results:
            return {}
        
        total_results = len(results)
        method_counts = {}
        total_cost = 0.0
        total_tokens = 0
        cached_count = 0
        
        user_count = 0
        assistant_count = 0
        
        confidence_sum = 0.0
        
        for result in results:
            # Count methods
            method_counts[result.method] = method_counts.get(result.method, 0) + 1
            
            # Sum costs and tokens
            total_cost += result.cost
            total_tokens += result.tokens_used
            
            # Count cached responses
            if result.cached:
                cached_count += 1
            
            # Count classifications
            if result.classification == "user":
                user_count += 1
            else:
                assistant_count += 1
            
            # Sum confidence
            confidence_sum += result.confidence
        
        return {
            "total_classifications": total_results,
            "user_classifications": user_count,
            "assistant_classifications": assistant_count,
            "methods_used": method_counts,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "cached_responses": cached_count,
            "cache_hit_rate": cached_count / total_results if total_results > 0 else 0,
            "average_confidence": confidence_sum / total_results if total_results > 0 else 0,
            "cost_per_classification": total_cost / total_results if total_results > 0 else 0
        }


class SmartClassificationPipeline:
    """Smart pipeline that adapts classification strategy based on content."""
    
    def __init__(self, openai_config: Optional[OpenAIConfig] = None):
        self.hybrid_classifier = HybridTextClassifier(openai_config)
        self.classification_history = []
    
    def process_conversation_segments(self, segments: List[str]) -> List[Tuple[str, str]]:
        """
        Process conversation segments with smart classification.
        
        Args:
            segments: List of text segments to classify
            
        Returns:
            List of (role, content) tuples
        """
        classified_segments = []
        context = []
        
        for segment in segments:
            # Classify with accumulated context
            result = self.hybrid_classifier.classify_text(segment, context)
            
            # Store result
            self.classification_history.append(result)
            
            # Add to output
            classified_segments.append((result.classification, segment))
            
            # Update context
            context.append(segment)
            
            # Keep context manageable (last 5 segments)
            if len(context) > 5:
                context = context[-5:]
        
        return classified_segments
    
    def get_processing_report(self) -> Dict[str, Any]:
        """Get comprehensive processing report."""
        if not self.classification_history:
            return {"message": "No classifications performed yet"}
        
        stats = self.hybrid_classifier.get_classification_stats(self.classification_history)
        
        # Add additional insights
        recent_results = self.classification_history[-10:]  # Last 10 classifications
        recent_stats = self.hybrid_classifier.get_classification_stats(recent_results)
        
        report = {
            "overall_stats": stats,
            "recent_stats": recent_stats,
            "ai_usage": {
                "ai_enabled": self.hybrid_classifier.ai_client is not None,
                "total_ai_calls": sum(1 for r in self.classification_history if "ai" in r.method),
                "ai_success_rate": self._calculate_ai_success_rate()
            },
            "recommendations": self._generate_recommendations(stats)
        }
        
        return report
    
    def _calculate_ai_success_rate(self) -> float:
        """Calculate AI classification success rate."""
        ai_results = [r for r in self.classification_history if "ai" in r.method]
        if not ai_results:
            return 0.0
        
        successful = sum(1 for r in ai_results if not r.reasoning.startswith("AI classification failed"))
        return successful / len(ai_results)
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on usage statistics."""
        recommendations = []
        
        # Cost optimization
        if stats.get("total_cost", 0) > 1.0:
            recommendations.append("Consider enabling caching to reduce API costs")
        
        # Confidence analysis
        avg_confidence = stats.get("average_confidence", 0)
        if avg_confidence < 0.7:
            recommendations.append("Low average confidence - consider adjusting classification thresholds")
        
        # Method distribution
        methods = stats.get("methods_used", {})
        if methods.get("rule_based", 0) > methods.get("ai_powered", 0) * 2:
            recommendations.append("Mostly using rule-based classification - AI might not be providing enough value")
        
        # Cache efficiency
        cache_rate = stats.get("cache_hit_rate", 0)
        if cache_rate < 0.3 and stats.get("total_cost", 0) > 0.5:
            recommendations.append("Low cache hit rate - consider increasing cache duration")
        
        return recommendations
    
    def optimize_for_cost(self):
        """Optimize settings for cost efficiency."""
        if self.hybrid_classifier.ai_client:
            # Increase confidence threshold to use AI less frequently
            self.hybrid_classifier.confidence_threshold = 0.9
            
            # Enable caching if not already enabled
            if self.hybrid_classifier.ai_client.config.enable_caching:
                self.hybrid_classifier.ai_client.config.cache_duration_hours = 48
    
    def optimize_for_accuracy(self):
        """Optimize settings for maximum accuracy."""
        if self.hybrid_classifier.ai_client:
            # Lower confidence threshold to use AI more frequently
            self.hybrid_classifier.confidence_threshold = 0.6
            
            # Use more sophisticated model if available
            if "gpt-4" in self.hybrid_classifier.ai_client.config.model:
                pass  # Already using advanced model
            else:
                print("Consider upgrading to GPT-4 for better accuracy")
    
    def clear_history(self):
        """Clear classification history."""
        self.classification_history = []
