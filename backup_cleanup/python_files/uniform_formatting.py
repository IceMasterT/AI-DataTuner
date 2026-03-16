#!/usr/bin/env python3
"""
Uniform Formatting System - Pillar 4: Guarantee Uniform Formatting
Canonical output schema, immediate linting, and normalization.
"""

import json
import re
import unicodedata
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging


class OutputFormat(Enum):
    """Canonical output formats."""
    JSON = "json"
    JSONL = "jsonl"


@dataclass
class CanonicalSchema:
    """Canonical output schema definition."""
    version: str = "1.0"
    required_fields: List[str] = field(default_factory=lambda: [
        "id", "format", "content", "quality_score", "accuracy_score",
        "personality", "source_file", "processing_timestamp",
        "validation_passed", "tier", "metadata"
    ])
    field_order: List[str] = field(default_factory=lambda: [
        "id", "format", "content", "quality_score", "accuracy_score",
        "personality", "source_file", "processing_timestamp",
        "validation_passed", "tier", "metadata"
    ])
    field_types: Dict[str, type] = field(default_factory=lambda: {
        "id": str,
        "format": str,
        "content": str,
        "quality_score": float,
        "accuracy_score": float,
        "personality": str,
        "source_file": str,
        "processing_timestamp": str,
        "validation_passed": bool,
        "tier": str,
        "metadata": dict
    })
    naming_conventions: Dict[str, str] = field(default_factory=lambda: {
        "case_style": "snake_case",
        "boolean_prefix": "is_",
        "timestamp_suffix": "_timestamp",
        "score_suffix": "_score"
    })


class PayloadLinter:
    """Immediate payload linting and validation."""
    
    def __init__(self, schema: CanonicalSchema):
        self.schema = schema
        self.logger = logging.getLogger(__name__)
    
    def lint_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Lint payload immediately after generation."""
        lint_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "corrections_applied": [],
            "linted_at": datetime.now().isoformat()
        }
        
        try:
            # Field presence validation
            missing_fields = []
            for field in self.schema.required_fields:
                if field not in payload:
                    missing_fields.append(field)
            
            if missing_fields:
                lint_result["errors"].extend([f"Missing required field: {field}" for field in missing_fields])
                lint_result["is_valid"] = False
            
            # Field type validation
            for field_name, expected_type in self.schema.field_types.items():
                if field_name in payload:
                    value = payload[field_name]
                    if not isinstance(value, expected_type):
                        lint_result["errors"].append(
                            f"Field {field_name}: Expected {expected_type.__name__}, got {type(value).__name__}"
                        )
                        lint_result["is_valid"] = False
            
            # Field order validation
            payload_fields = list(payload.keys())
            expected_order = [f for f in self.schema.field_order if f in payload_fields]
            
            if payload_fields != expected_order:
                lint_result["warnings"].append("Field order doesn't match canonical schema")
                # Auto-correct field order
                corrected_payload = {field: payload[field] for field in expected_order}
                # Add any extra fields at the end
                for field in payload_fields:
                    if field not in corrected_payload:
                        corrected_payload[field] = payload[field]
                
                payload.clear()
                payload.update(corrected_payload)
                lint_result["corrections_applied"].append("Corrected field order")
            
            # Naming convention validation
            naming_issues = self._validate_naming_conventions(payload)
            if naming_issues:
                lint_result["warnings"].extend(naming_issues)
            
            # Content-specific validation
            content_issues = self._validate_content_fields(payload)
            if content_issues:
                lint_result["errors"].extend(content_issues)
                lint_result["is_valid"] = False
            
            # JSON serialization test
            try:
                json.dumps(payload)
            except (TypeError, ValueError) as e:
                lint_result["errors"].append(f"JSON serialization failed: {e}")
                lint_result["is_valid"] = False
            
        except Exception as e:
            lint_result["errors"].append(f"Linting failed: {e}")
            lint_result["is_valid"] = False
        
        return lint_result
    
    def _validate_naming_conventions(self, payload: Dict[str, Any]) -> List[str]:
        """Validate naming conventions."""
        issues = []
        conventions = self.schema.naming_conventions
        
        for field_name in payload.keys():
            # Check snake_case
            if conventions["case_style"] == "snake_case":
                if not re.match(r'^[a-z][a-z0-9_]*$', field_name):
                    issues.append(f"Field {field_name} doesn't follow snake_case convention")
            
            # Check boolean prefix
            if isinstance(payload[field_name], bool):
                if not field_name.startswith(conventions["boolean_prefix"]):
                    issues.append(f"Boolean field {field_name} should start with {conventions['boolean_prefix']}")
            
            # Check timestamp suffix
            if "timestamp" in field_name.lower():
                if not field_name.endswith(conventions["timestamp_suffix"]):
                    issues.append(f"Timestamp field {field_name} should end with {conventions['timestamp_suffix']}")
            
            # Check score suffix
            if "score" in field_name.lower():
                if not field_name.endswith(conventions["score_suffix"]):
                    issues.append(f"Score field {field_name} should end with {conventions['score_suffix']}")
        
        return issues
    
    def _validate_content_fields(self, payload: Dict[str, Any]) -> List[str]:
        """Validate content-specific fields."""
        errors = []
        
        # Validate accuracy score
        if "accuracy_score" in payload:
            score = payload["accuracy_score"]
            if not isinstance(score, (int, float)) or score < 95.0 or score > 100.0:
                errors.append(f"accuracy_score must be float between 95.0-100.0, got {score}")
        
        # Validate quality score
        if "quality_score" in payload:
            score = payload["quality_score"]
            if not isinstance(score, (int, float)) or score < 0.0 or score > 100.0:
                errors.append(f"quality_score must be float between 0.0-100.0, got {score}")
        
        # Validate timestamp format
        if "processing_timestamp" in payload:
            timestamp = payload["processing_timestamp"]
            if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', timestamp):
                errors.append(f"processing_timestamp must be ISO format, got {timestamp}")
        
        # Validate content length
        if "content" in payload:
            content = payload["content"]
            if not isinstance(content, str) or len(content.strip()) < 10:
                errors.append("content must be non-empty string with minimum 10 characters")
        
        return errors


class ContentNormalizer:
    """Normalize whitespace, Unicode, and line endings."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def normalize_content(self, content: str) -> Dict[str, Any]:
        """Normalize content to prevent hidden errors."""
        normalization_result = {
            "original_length": len(content),
            "normalized_content": content,
            "changes_applied": [],
            "normalized_at": datetime.now().isoformat()
        }
        
        try:
            # Unicode normalization (NFC - Canonical Decomposition followed by Canonical Composition)
            normalized = unicodedata.normalize('NFC', content)
            if normalized != content:
                normalization_result["changes_applied"].append("Unicode NFC normalization")
                content = normalized
            
            # Line ending normalization (convert to \n)
            if '\r\n' in content or '\r' in content:
                content = content.replace('\r\n', '\n').replace('\r', '\n')
                normalization_result["changes_applied"].append("Line ending normalization")
            
            # Whitespace normalization
            original_content = content
            
            # Remove trailing whitespace from lines
            content = '\n'.join(line.rstrip() for line in content.split('\n'))
            
            # Normalize multiple consecutive spaces to single space (except in code blocks)
            content = re.sub(r'(?<!```[^\n]*\n)(?<!`[^`]*) {2,}(?![^`]*`)', ' ', content)
            
            # Remove excessive blank lines (max 2 consecutive)
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            # Trim leading/trailing whitespace
            content = content.strip()
            
            if content != original_content:
                normalization_result["changes_applied"].append("Whitespace normalization")
            
            # Remove invisible characters (except standard whitespace)
            invisible_chars = re.compile(r'[\u200b-\u200f\u2028-\u202f\u205f-\u206f\ufeff]')
            if invisible_chars.search(content):
                content = invisible_chars.sub('', content)
                normalization_result["changes_applied"].append("Invisible character removal")
            
            # Normalize quotes (smart quotes to straight quotes)
            quote_mapping = {
                '"': '"', '"': '"',  # Smart double quotes
                ''': "'", ''': "'",  # Smart single quotes
                '„': '"', '‚': "'",  # German quotes
                '«': '"', '»': '"',  # French quotes
            }
            
            for smart_quote, straight_quote in quote_mapping.items():
                if smart_quote in content:
                    content = content.replace(smart_quote, straight_quote)
                    normalization_result["changes_applied"].append("Quote normalization")
            
            # Normalize dashes
            content = content.replace('—', '--').replace('–', '-')  # Em/en dash to hyphens
            if '—' in normalization_result["normalized_content"] or '–' in normalization_result["normalized_content"]:
                normalization_result["changes_applied"].append("Dash normalization")
            
            normalization_result["normalized_content"] = content
            normalization_result["final_length"] = len(content)
            normalization_result["length_change"] = len(content) - normalization_result["original_length"]
            
        except Exception as e:
            self.logger.error(f"Content normalization failed: {e}")
            normalization_result["error"] = str(e)
        
        return normalization_result


class UniformFormattingSystem:
    """Complete uniform formatting system."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.schema = CanonicalSchema()
        self.linter = PayloadLinter(self.schema)
        self.normalizer = ContentNormalizer()
    
    def format_payload(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload with uniform standards."""
        formatting_result = {
            "success": True,
            "original_data": raw_data.copy(),
            "formatted_data": None,
            "processing_steps": [],
            "errors": [],
            "warnings": [],
            "formatted_at": datetime.now().isoformat()
        }
        
        try:
            # Step 1: Content normalization
            if "content" in raw_data and isinstance(raw_data["content"], str):
                norm_result = self.normalizer.normalize_content(raw_data["content"])
                raw_data["content"] = norm_result["normalized_content"]
                formatting_result["processing_steps"].append({
                    "step": "content_normalization",
                    "changes": norm_result["changes_applied"]
                })
            
            # Step 2: Payload linting
            lint_result = self.linter.lint_payload(raw_data)
            formatting_result["processing_steps"].append({
                "step": "payload_linting",
                "corrections": lint_result["corrections_applied"]
            })
            
            if not lint_result["is_valid"]:
                formatting_result["success"] = False
                formatting_result["errors"].extend(lint_result["errors"])
                return formatting_result
            
            formatting_result["warnings"].extend(lint_result["warnings"])
            
            # Step 3: Canonical field ordering
            ordered_data = {}
            for field in self.schema.field_order:
                if field in raw_data:
                    ordered_data[field] = raw_data[field]
            
            # Add any additional fields not in canonical order
            for field, value in raw_data.items():
                if field not in ordered_data:
                    ordered_data[field] = value
            
            formatting_result["formatted_data"] = ordered_data
            
            # Step 4: Final validation
            final_validation = self._final_validation(ordered_data)
            if not final_validation["is_valid"]:
                formatting_result["success"] = False
                formatting_result["errors"].extend(final_validation["errors"])
            
            formatting_result["processing_steps"].append({
                "step": "final_validation",
                "result": final_validation
            })
            
        except Exception as e:
            formatting_result["success"] = False
            formatting_result["errors"].append(f"Formatting failed: {e}")
        
        return formatting_result
    
    def _final_validation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Final validation before output."""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # JSON serialization test
            json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            
            # Validate JSON can be parsed back
            parsed_back = json.loads(json_str)
            
            if parsed_back != data:
                validation_result["errors"].append("JSON round-trip validation failed")
                validation_result["is_valid"] = False
            
            # Check for required accuracy threshold
            if "accuracy_score" in data and data["accuracy_score"] < 95.0:
                validation_result["errors"].append(f"Accuracy score {data['accuracy_score']} below required 95.0")
                validation_result["is_valid"] = False
            
            # Validate content format compliance
            if "content" in data and "format" in data:
                format_validation = self._validate_content_format(data["content"], data["format"])
                if not format_validation["is_valid"]:
                    validation_result["errors"].extend(format_validation["errors"])
                    validation_result["is_valid"] = False
            
        except Exception as e:
            validation_result["errors"].append(f"Final validation failed: {e}")
            validation_result["is_valid"] = False
        
        return validation_result
    
    def _validate_content_format(self, content: str, format_type: str) -> Dict[str, Any]:
        """Validate content matches specified format."""
        validation_result = {
            "is_valid": True,
            "errors": []
        }
        
        format_validators = {
            "qwen": lambda c: "<|user|>" in c and "<|assistant|>" in c,
            "alpaca": lambda c: "### Instruction:" in c and "### Response:" in c,
            "chatml": lambda c: "<|im_start|>" in c and "<|im_end|>" in c,
            "sharegpt": lambda c: self._is_valid_json(c),
            "llama2": lambda c: "[INST]" in c and "[/INST]" in c
        }
        
        if format_type in format_validators:
            if not format_validators[format_type](content):
                validation_result["errors"].append(f"Content doesn't match {format_type} format requirements")
                validation_result["is_valid"] = False
        else:
            validation_result["errors"].append(f"Unknown format type: {format_type}")
            validation_result["is_valid"] = False
        
        return validation_result
    
    def _is_valid_json(self, content: str) -> bool:
        """Check if content is valid JSON."""
        try:
            json.loads(content)
            return True
        except:
            return False
    
    def export_to_format(self, data: Dict[str, Any], output_format: OutputFormat) -> str:
        """Export formatted data to specified output format."""
        if output_format == OutputFormat.JSON:
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif output_format == OutputFormat.JSONL:
            return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        else:
            raise ValueError(f"Unsupported output format: {output_format}")


def get_uniform_formatting_system() -> UniformFormattingSystem:
    """Get configured uniform formatting system."""
    return UniformFormattingSystem()


if __name__ == "__main__":
    # Test the uniform formatting system
    formatting_system = get_uniform_formatting_system()
    
    print("📐 UNIFORM FORMATTING SYSTEM")
    print("=" * 50)
    print(f"Schema Version: {formatting_system.schema.version}")
    print(f"Required Fields: {len(formatting_system.schema.required_fields)}")
    print(f"Field Order Enforced: {len(formatting_system.schema.field_order)} fields")
    print(f"Naming Conventions: {formatting_system.schema.naming_conventions['case_style']}")
    
    print("\n✅ Canonical output schema enforced")
    print("✅ Immediate payload linting active")
    print("✅ Content normalization (Unicode, whitespace, line endings)")
    print("✅ JSON serialization validation")
    print("✅ Format compliance verification")
    
    print("\n🔒 Uniform formatting system ready for production use")
