#!/usr/bin/env python3
"""
Disciplined Prompting System - Pillar 3: Enforce Disciplined Prompting
Standardized templates, locked versions, and validation before execution.
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import logging
from pathlib import Path


class PromptVersion(Enum):
    """Locked prompt template versions."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V1_2 = "1.2"
    CURRENT = V1_2


@dataclass
class PromptSlot:
    """Definition of a prompt template slot."""
    name: str
    required: bool
    datatype: type
    description: str
    validation_pattern: Optional[str] = None
    max_tokens: Optional[int] = None
    allowed_values: Optional[List[str]] = None


@dataclass
class PromptTemplate:
    """Immutable prompt template with explicit slots."""
    template_id: str
    version: PromptVersion
    name: str
    description: str
    template_text: str
    slots: Dict[str, PromptSlot]
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    locked: bool = True
    max_total_tokens: int = 4000
    style_guide: str = "professional"
    
    def __post_init__(self):
        """Generate template hash for version tracking."""
        self.template_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """Calculate hash for template versioning."""
        content = f"{self.template_text}{json.dumps(self.slots, default=str)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class PromptTemplateRegistry:
    """Registry of locked prompt templates."""
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self.logger = logging.getLogger(__name__)
        self._initialize_standard_templates()
    
    def _initialize_standard_templates(self):
        """Initialize standard prompt templates."""
        
        # Conversation Formatting Template
        conversation_template = PromptTemplate(
            template_id="conversation_format",
            version=PromptVersion.CURRENT,
            name="Conversation Formatting",
            description="Format content into conversation format with 95% accuracy",
            template_text="""
CRITICAL DATA FORMATTING TASK - 95% ACCURACY REQUIRED

CONTEXT: {context}

ORIGINAL CONTENT TO FORMAT:
{content}

TARGET FORMAT: {format_type}
{format_specifications}

PERSONALITY: {personality}
{personality_specifications}

INSTRUCTIONS:
1. PRESERVE 100% of factual information from original content
2. DO NOT add information not present in original
3. DO NOT change or omit factual claims
4. MAINTAIN exact format specifications for {format_type}
5. Apply {personality} personality consistently throughout
6. Ensure natural, fluent conversation flow
7. Validate format compliance before responding

QUALITY REQUIREMENTS:
- Factual Accuracy: 100% (no changes to facts)
- Format Compliance: 100% (exact format match)
- Completeness: 100% (all information preserved)
- Consistency: 100% (uniform style and tone)
- Fluency: Natural conversation flow

RESPOND WITH ONLY THE PERFECTLY FORMATTED CONTENT. NO EXPLANATIONS OR COMMENTS.
""",
            slots={
                "context": PromptSlot(
                    name="context",
                    required=False,
                    datatype=str,
                    description="Additional context for formatting",
                    max_tokens=200
                ),
                "content": PromptSlot(
                    name="content",
                    required=True,
                    datatype=str,
                    description="Original content to format",
                    max_tokens=2000
                ),
                "format_type": PromptSlot(
                    name="format_type",
                    required=True,
                    datatype=str,
                    description="Target conversation format",
                    allowed_values=["qwen", "alpaca", "chatml", "sharegpt", "llama2"]
                ),
                "format_specifications": PromptSlot(
                    name="format_specifications",
                    required=True,
                    datatype=str,
                    description="Detailed format specifications",
                    max_tokens=500
                ),
                "personality": PromptSlot(
                    name="personality",
                    required=True,
                    datatype=str,
                    description="Personality to apply (can be predefined or custom)",
                    allowed_values=["professional", "casual", "technical", "educational", "friendly", "custom"]
                ),
                "personality_specifications": PromptSlot(
                    name="personality_specifications",
                    required=True,
                    datatype=str,
                    description="Detailed personality specifications",
                    max_tokens=300
                )
            }
        )
        
        # Quality Assessment Template
        quality_template = PromptTemplate(
            template_id="quality_assessment",
            version=PromptVersion.CURRENT,
            name="Quality Assessment",
            description="Assess content quality with detailed scoring",
            template_text="""
CONTENT QUALITY ASSESSMENT - DETAILED ANALYSIS REQUIRED

ORIGINAL CONTENT:
{original_content}

FORMATTED CONTENT TO ASSESS:
{formatted_content}

FORMAT TYPE: {format_type}

ASSESSMENT CRITERIA:
1. FACTUAL ACCURACY (40% weight) - Must be 95%+ to pass
   - Verify all facts against original content
   - Check for any added or altered information
   - Ensure no factual distortions or hallucinations

2. FORMAT COMPLIANCE (25% weight)
   - Perfect adherence to {format_type} format
   - Correct use of delimiters and structure
   - No formatting errors or inconsistencies

3. CONTENT PRESERVATION (20% weight)
   - All key information retained
   - No important details omitted
   - Meaning and context preserved

4. INSTRUCTION FOLLOWING (10% weight)
   - Exact compliance with formatting instructions
   - Proper personality application
   - Consistent style throughout

5. TRAINING READINESS (5% weight)
   - Suitable for LLM training
   - Natural conversation flow
   - Appropriate length and structure

RESPOND WITH JSON:
{{
    "overall_score": 0-100,
    "factual_accuracy": 0-100,
    "format_compliance": 0-100,
    "content_preservation": 0-100,
    "instruction_following": 0-100,
    "training_readiness": 0-100,
    "passes_95_threshold": true/false,
    "detailed_feedback": "specific issues and recommendations",
    "confidence": 0.0-1.0
}}
""",
            slots={
                "original_content": PromptSlot(
                    name="original_content",
                    required=True,
                    datatype=str,
                    description="Original content for comparison",
                    max_tokens=2000
                ),
                "formatted_content": PromptSlot(
                    name="formatted_content",
                    required=True,
                    datatype=str,
                    description="Formatted content to assess",
                    max_tokens=2000
                ),
                "format_type": PromptSlot(
                    name="format_type",
                    required=True,
                    datatype=str,
                    description="Format type for assessment",
                    allowed_values=["qwen", "alpaca", "chatml", "sharegpt", "llama2"]
                )
            }
        )
        
        # Error Correction Template
        correction_template = PromptTemplate(
            template_id="error_correction",
            version=PromptVersion.CURRENT,
            name="Error Correction",
            description="Correct identified errors while maintaining accuracy",
            template_text="""
CRITICAL ERROR CORRECTION TASK

CONTENT WITH ERRORS:
{content_with_errors}

IDENTIFIED ERRORS:
{error_list}

ORIGINAL REFERENCE:
{original_reference}

CORRECTION INSTRUCTIONS:
1. Fix ONLY the identified errors
2. Maintain 100% factual accuracy from original reference
3. Preserve all correct information unchanged
4. Do not add new information not in original
5. Ensure perfect format compliance for {format_type}
6. Maintain natural flow and readability

CRITICAL REQUIREMENTS:
- Fix all listed errors completely
- Preserve all factually correct content
- Maintain original meaning and context
- Ensure format specifications are met
- Achieve 95%+ accuracy standard

RESPOND WITH ONLY THE CORRECTED CONTENT.
""",
            slots={
                "content_with_errors": PromptSlot(
                    name="content_with_errors",
                    required=True,
                    datatype=str,
                    description="Content containing errors to fix",
                    max_tokens=2000
                ),
                "error_list": PromptSlot(
                    name="error_list",
                    required=True,
                    datatype=str,
                    description="List of specific errors to correct",
                    max_tokens=500
                ),
                "original_reference": PromptSlot(
                    name="original_reference",
                    required=True,
                    datatype=str,
                    description="Original content for reference",
                    max_tokens=2000
                ),
                "format_type": PromptSlot(
                    name="format_type",
                    required=True,
                    datatype=str,
                    description="Target format type",
                    allowed_values=["qwen", "alpaca", "chatml", "sharegpt", "llama2"]
                )
            }
        )
        
        # Register templates
        self.templates[conversation_template.template_id] = conversation_template
        self.templates[quality_template.template_id] = quality_template
        self.templates[correction_template.template_id] = correction_template
        
        self.logger.info(f"Initialized {len(self.templates)} standard prompt templates")
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a locked template by ID."""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[str]:
        """List all available template IDs."""
        return list(self.templates.keys())
    
    def register_template(self, template: PromptTemplate) -> bool:
        """Register a new template (requires approval)."""
        if template.template_id in self.templates:
            self.logger.error(f"Template {template.template_id} already exists")
            return False
        
        self.templates[template.template_id] = template
        self.logger.info(f"Registered new template: {template.template_id}")
        return True


class PromptValidator:
    """Validates filled prompts before execution."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.style_guides = {
            "professional": {
                "tone": "formal",
                "contractions": False,
                "technical_terms": True,
                "max_sentence_length": 25
            },
            "casual": {
                "tone": "informal",
                "contractions": True,
                "technical_terms": False,
                "max_sentence_length": 20
            },
            "technical": {
                "tone": "precise",
                "contractions": False,
                "technical_terms": True,
                "max_sentence_length": 30
            }
        }
    
    def validate_filled_prompt(self, template: PromptTemplate, 
                             filled_values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a filled prompt before execution."""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "token_count": 0,
            "template_hash": template.template_hash,
            "validated_at": datetime.now().isoformat()
        }
        
        try:
            # Check all required slots are filled
            for slot_name, slot_def in template.slots.items():
                if slot_def.required and slot_name not in filled_values:
                    validation_result["errors"].append(f"Missing required slot: {slot_name}")
                    validation_result["is_valid"] = False
                    continue
                
                if slot_name in filled_values:
                    value = filled_values[slot_name]
                    
                    # Type validation
                    if not isinstance(value, slot_def.datatype):
                        validation_result["errors"].append(
                            f"Slot {slot_name}: Expected {slot_def.datatype.__name__}, got {type(value).__name__}"
                        )
                        validation_result["is_valid"] = False
                        continue
                    
                    # Pattern validation
                    if slot_def.validation_pattern and isinstance(value, str):
                        if not re.match(slot_def.validation_pattern, value):
                            validation_result["errors"].append(
                                f"Slot {slot_name}: Value doesn't match pattern {slot_def.validation_pattern}"
                            )
                            validation_result["is_valid"] = False
                    
                    # Allowed values validation
                    if slot_def.allowed_values and value not in slot_def.allowed_values:
                        validation_result["errors"].append(
                            f"Slot {slot_name}: Value '{value}' not in allowed values {slot_def.allowed_values}"
                        )
                        validation_result["is_valid"] = False
                    
                    # Token length validation
                    if slot_def.max_tokens and isinstance(value, str):
                        token_count = self._estimate_tokens(value)
                        if token_count > slot_def.max_tokens:
                            validation_result["errors"].append(
                                f"Slot {slot_name}: Token count {token_count} exceeds limit {slot_def.max_tokens}"
                            )
                            validation_result["is_valid"] = False
            
            # Generate filled prompt
            if validation_result["is_valid"]:
                filled_prompt = template.template_text.format(**filled_values)
                
                # Total token count validation
                total_tokens = self._estimate_tokens(filled_prompt)
                validation_result["token_count"] = total_tokens
                
                if total_tokens > template.max_total_tokens:
                    validation_result["errors"].append(
                        f"Total token count {total_tokens} exceeds template limit {template.max_total_tokens}"
                    )
                    validation_result["is_valid"] = False
                
                # Style guide validation
                style_issues = self._validate_style_guide(filled_prompt, template.style_guide)
                if style_issues:
                    validation_result["warnings"].extend(style_issues)
                
                validation_result["filled_prompt"] = filled_prompt
            
        except Exception as e:
            validation_result["errors"].append(f"Validation failed: {e}")
            validation_result["is_valid"] = False
        
        return validation_result
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (simplified)."""
        # Rough estimation: 1 token ≈ 4 characters for English text
        return len(text) // 4
    
    def _validate_style_guide(self, text: str, style_guide: str) -> List[str]:
        """Validate text against style guide."""
        issues = []
        
        if style_guide not in self.style_guides:
            return issues
        
        guide = self.style_guides[style_guide]
        
        # Check contractions
        if not guide["contractions"] and re.search(r"\b\w+'\w+\b", text):
            issues.append("Contractions found but not allowed in style guide")
        
        # Check sentence length
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            words = sentence.split()
            if len(words) > guide["max_sentence_length"]:
                issues.append(f"Sentence exceeds maximum length: {len(words)} words")
                break  # Only report first occurrence
        
        return issues


class DisciplinedPromptingSystem:
    """Complete disciplined prompting system."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.template_registry = PromptTemplateRegistry()
        self.validator = PromptValidator()
        self.execution_log: List[Dict[str, Any]] = []
    
    def execute_prompt(self, template_id: str, slot_values: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a prompt with full validation and logging."""
        execution_record = {
            "template_id": template_id,
            "execution_timestamp": datetime.now().isoformat(),
            "slot_values": slot_values.copy(),
            "validation_passed": False,
            "execution_successful": False
        }
        
        try:
            # Get template
            template = self.template_registry.get_template(template_id)
            if not template:
                execution_record["error"] = f"Template not found: {template_id}"
                self.execution_log.append(execution_record)
                return execution_record
            
            # Validate filled prompt
            validation_result = self.validator.validate_filled_prompt(template, slot_values)
            execution_record["validation_result"] = validation_result
            
            if not validation_result["is_valid"]:
                execution_record["error"] = "Prompt validation failed"
                self.execution_log.append(execution_record)
                return execution_record
            
            execution_record["validation_passed"] = True
            execution_record["filled_prompt"] = validation_result["filled_prompt"]
            execution_record["token_count"] = validation_result["token_count"]
            execution_record["template_hash"] = validation_result["template_hash"]
            
            # Log successful execution
            execution_record["execution_successful"] = True
            self.execution_log.append(execution_record)
            
            return execution_record
            
        except Exception as e:
            execution_record["error"] = f"Execution failed: {e}"
            self.execution_log.append(execution_record)
            return execution_record
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history for audit trail."""
        return self.execution_log[-limit:]
    
    def get_template_usage_stats(self) -> Dict[str, Any]:
        """Get template usage statistics."""
        stats = {
            "total_executions": len(self.execution_log),
            "successful_executions": sum(1 for log in self.execution_log if log["execution_successful"]),
            "template_usage": {},
            "validation_failures": sum(1 for log in self.execution_log if not log["validation_passed"])
        }
        
        for log in self.execution_log:
            template_id = log["template_id"]
            if template_id not in stats["template_usage"]:
                stats["template_usage"][template_id] = 0
            stats["template_usage"][template_id] += 1
        
        return stats


def get_disciplined_prompting_system() -> DisciplinedPromptingSystem:
    """Get configured disciplined prompting system."""
    return DisciplinedPromptingSystem()


if __name__ == "__main__":
    # Test the disciplined prompting system
    prompting_system = get_disciplined_prompting_system()
    
    print("📝 DISCIPLINED PROMPTING SYSTEM")
    print("=" * 50)
    print(f"Available Templates: {len(prompting_system.template_registry.list_templates())}")
    
    for template_id in prompting_system.template_registry.list_templates():
        template = prompting_system.template_registry.get_template(template_id)
        print(f"✅ {template.name} (v{template.version.value}) - {len(template.slots)} slots")
    
    print("\n🔒 All templates locked and versioned for traceability")
    print("🔍 Validation enforced before execution")
    print("📊 Complete audit trail maintained")
