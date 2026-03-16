#!/usr/bin/env python3
"""
LLM-powered Quality Scorer for Phase 4 of the pipeline.
Evaluates data quality and personality depth using AI assessment.
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from openai_integration import OpenAIClient, OpenAIConfig
from env_config import get_config


@dataclass
class QualityScore:
    """Quality score result."""

    overall_score: float
    accuracy_score: float
    fluency_score: float
    personality_depth_score: float
    coherence_score: float
    training_readiness_score: float
    feedback: str
    confidence: float
    cost: float
    processing_time: float


@dataclass
class QualityReport:
    """Comprehensive quality report."""

    summary: Dict[str, Any]
    individual_scores: List[QualityScore]
    recommendations: List[str]
    overall_grade: str
    generated_at: str
    total_cost: float


class LLMQualityScorer:
    """LLM-powered quality assessment system."""

    def __init__(
        self,
        model: str = "gpt-4o",
        metrics: List[str] = None,
        target_accuracy: float = 95.0,
    ):
        """
        Initialize the enhanced quality scorer.

        Args:
            model: OpenAI model to use for scoring
            metrics: List of metrics to evaluate
            target_accuracy: Minimum accuracy target (default 95%)
        """
        self.model = model
        self.target_accuracy = target_accuracy
        self.metrics = metrics or [
            "factual_accuracy",
            "format_compliance",
            "content_preservation",
            "instruction_following",
            "consistency",
            "completeness",
            "fluency",
            "personality_depth",
            "training_readiness",
        ]
        self.logger = logging.getLogger(__name__)

        # Initialize OpenAI client
        config = get_config()
        if config.openai_api_key:
            provider = getattr(config, "openai_provider", "openai")
            provider_base_url = None
            if provider == "openrouter":
                provider_base_url = getattr(config, "openrouter_base_url", None)
            elif provider == "lmstudio":
                provider_base_url = getattr(config, "lmstudio_base_url", None)
            elif provider == "ollama":
                provider_base_url = getattr(config, "ollama_base_url", None)

            ai_config = OpenAIConfig(
                provider=provider,
                api_key=config.openai_api_key,
                model=model,
                base_url=provider_base_url,
                app_name=getattr(config, "openrouter_app_name", "AI Data Pipeline"),
                app_url=getattr(config, "openrouter_site_url", None),
                cost_limit_per_day=config.daily_cost_limit,
            )
            self.ai_client = OpenAIClient(ai_config)
        else:
            self.ai_client = None

        # Initialize enhanced accuracy system
        try:
            from enhanced_accuracy_system import EnhancedAccuracySystem

            self.accuracy_system = EnhancedAccuracySystem(target_accuracy)
        except ImportError:
            self.logger.warning("Enhanced accuracy system not available")
            self.accuracy_system = None
            self.logger.warning(
                "No OpenAI API key available - quality scoring will use rule-based fallbacks"
            )

    def score_content(
        self,
        content: str,
        context: Dict[str, Any] = None,
        original_content: str = None,
        format_type: str = None,
    ) -> QualityScore:
        """
        Score content quality using LLM evaluation.

        Args:
            content: Text content to score
            context: Additional context for scoring

        Returns:
            QualityScore with detailed metrics
        """
        start_time = time.time()

        if self.ai_client:
            return self._score_with_ai(content, context, start_time)
        else:
            return self._score_with_rules(content, context, start_time)

    def _score_with_ai(
        self, content: str, context: Dict[str, Any], start_time: float
    ) -> QualityScore:
        """Score content using enhanced AI evaluation with 95% accuracy focus."""
        # Check if enhanced accuracy system is available
        original_content = context.get("original_content")
        format_type = context.get("format_type")

        if self.accuracy_system and original_content and format_type:
            try:
                validation_result = self.accuracy_system.validate_and_enhance(
                    content, format_type, original_content
                )

                metrics = validation_result.metrics

                return QualityScore(
                    overall_score=metrics.factual_accuracy,
                    accuracy_score=metrics.factual_accuracy,
                    fluency_score=metrics.consistency_score,
                    personality_depth_score=85.0,  # Default for now
                    coherence_score=metrics.consistency_score,
                    training_readiness_score=metrics.instruction_following,
                    feedback=self._generate_enhanced_feedback(validation_result),
                    confidence=metrics.confidence_level,
                    cost=metrics.cost,
                    processing_time=metrics.processing_time,
                )

            except Exception as e:
                self.logger.error(f"Enhanced accuracy scoring failed: {e}")

        # Fallback to standard AI scoring with enhanced prompts
        system_prompt = self._build_enhanced_scoring_prompt()
        user_prompt = self._build_enhanced_user_prompt(content, context)

        try:
            result = self.ai_client.make_request(user_prompt, system_prompt)

            # Parse AI response
            response_text = result["response"]
            scores = self._parse_ai_scores(response_text)

            # Ensure accuracy meets minimum threshold
            accuracy_score = scores.get("accuracy", 0)
            if accuracy_score < self.target_accuracy:
                scores["feedback"] += (
                    f" WARNING: Accuracy {accuracy_score}% below target {self.target_accuracy}%"
                )
                scores["overall"] = min(scores.get("overall", 0), accuracy_score)

            return QualityScore(
                overall_score=scores.get("overall", 0),
                accuracy_score=accuracy_score,
                fluency_score=scores.get("fluency", 0),
                personality_depth_score=scores.get("personality_depth", 0),
                coherence_score=scores.get("coherence", 0),
                training_readiness_score=scores.get("training_readiness", 0),
                feedback=scores.get("feedback", ""),
                confidence=scores.get("confidence", 0.8),
                cost=result["cost"],
                processing_time=time.time() - start_time,
            )

        except Exception as e:
            self.logger.error(f"AI scoring failed: {e}")
            return self._score_with_rules(content, context, start_time)

    def _generate_enhanced_feedback(self, validation_result) -> str:
        """Generate enhanced feedback from validation result."""
        feedback_parts = []

        if validation_result.is_valid:
            feedback_parts.append(
                f"✅ VALIDATION PASSED - Accuracy: {validation_result.accuracy_score:.1f}%"
            )
        else:
            feedback_parts.append(
                f"❌ VALIDATION FAILED - Accuracy: {validation_result.accuracy_score:.1f}%"
            )

        if validation_result.errors:
            feedback_parts.append(f"Errors: {'; '.join(validation_result.errors[:3])}")

        if validation_result.warnings:
            feedback_parts.append(
                f"Warnings: {'; '.join(validation_result.warnings[:2])}"
            )

        if validation_result.corrections:
            feedback_parts.append(
                f"Corrections applied: {len(validation_result.corrections)}"
            )

        return " | ".join(feedback_parts)

    def _build_enhanced_scoring_prompt(self) -> str:
        """Build enhanced system prompt for 95% accuracy focus."""
        return f"""You are an expert quality assessor for LLM training data with a focus on achieving 95%+ accuracy.

CRITICAL EVALUATION CRITERIA:
1. FACTUAL ACCURACY (Weight: 40%) - Must be 95%+ to pass
   - Verify all facts against original content
   - Check for any added or altered information
   - Ensure no factual distortions or hallucinations

2. FORMAT COMPLIANCE (Weight: 25%)
   - Perfect adherence to specified format
   - Correct use of delimiters and structure
   - No formatting errors or inconsistencies

3. CONTENT PRESERVATION (Weight: 20%)
   - All key information retained
   - No important details omitted
   - Meaning and context preserved

4. INSTRUCTION FOLLOWING (Weight: 10%)
   - Exact compliance with formatting instructions
   - Proper personality application
   - Consistent style throughout

5. TRAINING READINESS (Weight: 5%)
   - Suitable for LLM training
   - Natural conversation flow
   - Appropriate length and structure

SCORING SCALE: 0-100 for each metric
MINIMUM ACCEPTABLE: 95% factual accuracy
RESPONSE FORMAT: JSON with scores and detailed feedback"""

    def _build_enhanced_user_prompt(self, content: str, context: Dict[str, Any]) -> str:
        """Build enhanced user prompt with context."""
        original_content = context.get("original_content", "Not provided")
        format_type = context.get("format_type", "Unknown")

        return f"""EVALUATE THIS CONTENT FOR 95%+ ACCURACY:

ORIGINAL CONTENT:
{original_content}

FORMATTED CONTENT TO EVALUATE:
{content}

FORMAT TYPE: {format_type}

Provide detailed scoring in JSON format:
{{
    "overall": 0-100,
    "accuracy": 0-100,
    "fluency": 0-100,
    "personality_depth": 0-100,
    "coherence": 0-100,
    "training_readiness": 0-100,
    "feedback": "detailed feedback with specific issues",
    "confidence": 0.0-1.0,
    "passes_95_threshold": true/false
}}

CRITICAL: If accuracy is below 95%, explain specific issues and mark as failed."""

    def _build_scoring_prompt(self) -> str:
        """Build the system prompt for AI scoring."""
        return """You are an expert evaluator of training data for large language models. 
Your task is to assess the quality of text content across multiple dimensions.

Evaluate the content on a scale of 0-100 for each metric:

1. ACCURACY (0-100): How factually correct and reliable is the information?
2. FLUENCY (0-100): How natural, grammatically correct, and well-written is the text?
3. PERSONALITY_DEPTH (0-100): How well does the text exhibit the intended personality/voice?
4. COHERENCE (0-100): How logical, consistent, and well-structured is the content?
5. TRAINING_READINESS (0-100): How suitable is this content for LLM fine-tuning?

Respond in this exact JSON format:
{
  "accuracy": <score>,
  "fluency": <score>,
  "personality_depth": <score>,
  "coherence": <score>,
  "training_readiness": <score>,
  "overall": <average_score>,
  "confidence": <0.0-1.0>,
  "feedback": "<brief explanation of scores and suggestions>"
}

Be objective, consistent, and provide constructive feedback."""

    def _build_user_prompt(self, content: str, context: Dict[str, Any]) -> str:
        """Build the user prompt with content to evaluate."""
        prompt = f"Please evaluate this training data content:\n\n{content}\n\n"

        if context:
            prompt += "Additional context:\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"

        prompt += "Provide your evaluation in the specified JSON format."
        return prompt

    def _parse_ai_scores(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response to extract scores."""
        try:
            # Try to find JSON in the response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                scores = json.loads(json_str)
                return scores
            else:
                # Fallback parsing
                return self._fallback_parse_scores(response_text)

        except json.JSONDecodeError:
            return self._fallback_parse_scores(response_text)

    def _fallback_parse_scores(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails."""
        import re

        scores = {}

        # Extract numeric scores
        patterns = {
            "accuracy": r"accuracy[:\s]+(\d+)",
            "fluency": r"fluency[:\s]+(\d+)",
            "personality_depth": r"personality[_\s]*depth[:\s]+(\d+)",
            "coherence": r"coherence[:\s]+(\d+)",
            "training_readiness": r"training[_\s]*readiness[:\s]+(\d+)",
            "overall": r"overall[:\s]+(\d+)",
            "confidence": r"confidence[:\s]+([0-9.]+)",
        }

        for metric, pattern in patterns.items():
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if metric == "confidence":
                    scores[metric] = min(1.0, value)
                else:
                    scores[metric] = min(100, value)

        # Calculate overall if missing
        if "overall" not in scores:
            metric_scores = [
                scores.get(m, 50)
                for m in [
                    "accuracy",
                    "fluency",
                    "personality_depth",
                    "coherence",
                    "training_readiness",
                ]
            ]
            scores["overall"] = sum(metric_scores) / len(metric_scores)

        # Add default values for missing scores
        defaults = {
            "accuracy": 50,
            "fluency": 50,
            "personality_depth": 50,
            "coherence": 50,
            "training_readiness": 50,
            "overall": 50,
            "confidence": 0.5,
            "feedback": "Automated scoring",
        }

        for key, default_value in defaults.items():
            if key not in scores:
                scores[key] = default_value

        return scores

    def _score_with_rules(
        self, content: str, context: Dict[str, Any], start_time: float
    ) -> QualityScore:
        """Fallback rule-based scoring."""
        # Simple rule-based metrics
        word_count = len(content.split())
        sentence_count = len([s for s in content.split(".") if s.strip()])

        # Basic quality heuristics
        accuracy_score = min(
            100, max(0, 70 + (word_count - 50) * 0.1)
        )  # Longer = potentially more accurate
        fluency_score = min(
            100, max(0, 60 + sentence_count * 2)
        )  # More sentences = better structure
        personality_depth_score = 50  # Neutral for rule-based
        coherence_score = min(
            100, max(0, 65 + (sentence_count - 3) * 3)
        )  # Reasonable sentence count
        training_readiness_score = min(
            100, max(0, 70 if 20 <= word_count <= 200 else 40)
        )  # Good length range

        overall_score = (
            accuracy_score
            + fluency_score
            + personality_depth_score
            + coherence_score
            + training_readiness_score
        ) / 5

        return QualityScore(
            overall_score=overall_score,
            accuracy_score=accuracy_score,
            fluency_score=fluency_score,
            personality_depth_score=personality_depth_score,
            coherence_score=coherence_score,
            training_readiness_score=training_readiness_score,
            feedback="Rule-based scoring (AI not available)",
            confidence=0.6,
            cost=0.0,
            processing_time=time.time() - start_time,
        )

    def batch_score_content(
        self, content_list: List[str], contexts: List[Dict[str, Any]] = None
    ) -> List[QualityScore]:
        """Score multiple content pieces efficiently."""
        if contexts is None:
            contexts = [{}] * len(content_list)

        scores = []
        for i, content in enumerate(content_list):
            context = contexts[i] if i < len(contexts) else {}
            score = self.score_content(content, context)
            scores.append(score)

        return scores

    def generate_quality_report(
        self, scores: List[QualityScore], metadata: Dict[str, Any] = None
    ) -> QualityReport:
        """Generate a comprehensive quality report."""
        if not scores:
            return QualityReport(
                summary={},
                individual_scores=[],
                recommendations=[],
                overall_grade="N/A",
                generated_at=datetime.now().isoformat(),
                total_cost=0.0,
            )

        # Calculate summary statistics
        summary = self.calculate_averages(scores)
        total_cost = sum(score.cost for score in scores)

        # Generate recommendations
        recommendations = self._generate_recommendations(summary)

        # Assign overall grade
        overall_grade = self._assign_grade(summary["overall"])

        return QualityReport(
            summary=summary,
            individual_scores=scores,
            recommendations=recommendations,
            overall_grade=overall_grade,
            generated_at=datetime.now().isoformat(),
            total_cost=total_cost,
        )

    def calculate_averages(self, scores: List[QualityScore]) -> Dict[str, float]:
        """Calculate average scores across all metrics."""
        if not scores:
            return {}

        metrics = [
            "overall_score",
            "accuracy_score",
            "fluency_score",
            "personality_depth_score",
            "coherence_score",
            "training_readiness_score",
        ]

        averages = {}
        for metric in metrics:
            values = [getattr(score, metric) for score in scores]
            averages[metric.replace("_score", "")] = sum(values) / len(values)

        return averages

    def _generate_recommendations(self, summary: Dict[str, float]) -> List[str]:
        """Generate recommendations based on scores."""
        recommendations = []

        if summary.get("accuracy", 0) < 70:
            recommendations.append(
                "Consider fact-checking and improving content accuracy"
            )

        if summary.get("fluency", 0) < 70:
            recommendations.append("Review grammar and writing quality")

        if summary.get("personality_depth", 0) < 60:
            recommendations.append("Strengthen personality voice and consistency")

        if summary.get("coherence", 0) < 70:
            recommendations.append("Improve logical flow and structure")

        if summary.get("training_readiness", 0) < 70:
            recommendations.append("Optimize content length and format for training")

        if summary.get("overall", 0) > 85:
            recommendations.append("Excellent quality! Content is ready for training")
        elif summary.get("overall", 0) > 70:
            recommendations.append("Good quality with minor improvements needed")
        else:
            recommendations.append("Significant improvements needed before training")

        return recommendations

    def _assign_grade(self, overall_score: float) -> str:
        """Assign letter grade based on overall score."""
        if overall_score >= 90:
            return "A"
        elif overall_score >= 80:
            return "B"
        elif overall_score >= 70:
            return "C"
        elif overall_score >= 60:
            return "D"
        else:
            return "F"

    def export_report(self, report: QualityReport, file_path: str) -> bool:
        """Export quality report to file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(asdict(report), f, indent=2, default=str)
            return True
        except Exception as e:
            self.logger.error(f"Error exporting report: {e}")
            return False


def main():
    """Test the quality scorer."""
    scorer = LLMQualityScorer()

    sample_content = """
    Machine learning is a powerful technology that enables computers to learn from data. 
    It's like teaching a computer to recognize patterns, just like how you might learn to 
    recognize your friend's voice on the phone. The more data we give the computer, the 
    better it becomes at making predictions and decisions.
    """

    print("Scoring sample content...")
    score = scorer.score_content(sample_content)

    print(f"Overall Score: {score.overall_score:.1f}")
    print(f"Accuracy: {score.accuracy_score:.1f}")
    print(f"Fluency: {score.fluency_score:.1f}")
    print(f"Personality Depth: {score.personality_depth_score:.1f}")
    print(f"Coherence: {score.coherence_score:.1f}")
    print(f"Training Readiness: {score.training_readiness_score:.1f}")
    print(f"Feedback: {score.feedback}")


if __name__ == "__main__":
    main()
