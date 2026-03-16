#!/usr/bin/env python3
"""
Data Contract Definition - Pillar 1: Define "Perfect Data" Up-Front
Formal data contract with required fields, datatypes, ranges, and schema versions.
Immutable until entire team signs off.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import json
import re
from datetime import datetime
import hashlib


class SchemaVersion(Enum):
    """Immutable schema versions - require team sign-off to change."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    CURRENT = V1_1


class DataFormat(Enum):
    """Allowable data formats."""
    QWEN = "qwen"
    ALPACA = "alpaca"
    CHATML = "chatml"
    SHAREGPT = "sharegpt"
    LLAMA2 = "llama2"


class QualityTier(Enum):
    """Quality tiers for data classification."""
    PREMIUM = "premium"      # 95%+ quality score
    STANDARD = "standard"    # 85-94% quality score
    BASIC = "basic"         # 70-84% quality score
    REMEDIATION = "remediation"  # <70% quality score


@dataclass
class DataContractField:
    """Definition of a required data field."""
    name: str
    datatype: type
    required: bool
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    description: str = ""


@dataclass
class PerfectDataContract:
    """
    IMMUTABLE DATA CONTRACT - Defines "Perfect Data"
    Changes require unanimous team sign-off and version increment.
    """
    
    # Contract metadata
    version: SchemaVersion = SchemaVersion.CURRENT
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    team_signoff: List[str] = field(default_factory=list)
    
    # Required fields for perfect data
    required_fields: Dict[str, DataContractField] = field(default_factory=lambda: {
        "id": DataContractField(
            name="id",
            datatype=str,
            required=True,
            min_length=8,
            max_length=64,
            pattern=r"^[a-zA-Z0-9_-]+$",
            description="Unique identifier for data record"
        ),
        "format": DataContractField(
            name="format",
            datatype=str,
            required=True,
            allowed_values=[f.value for f in DataFormat],
            description="Conversation format type"
        ),
        "content": DataContractField(
            name="content",
            datatype=str,
            required=True,
            min_length=10,
            max_length=8192,
            description="Formatted conversation content"
        ),
        "quality_score": DataContractField(
            name="quality_score",
            datatype=float,
            required=True,
            min_length=0.0,
            max_length=100.0,
            description="Quality score (0-100)"
        ),
        "accuracy_score": DataContractField(
            name="accuracy_score",
            datatype=float,
            required=True,
            min_length=95.0,  # MINIMUM 95% accuracy required
            max_length=100.0,
            description="Accuracy score (95-100 required)"
        ),
        "personality": DataContractField(
            name="personality",
            datatype=str,
            required=True,
            allowed_values=["professional", "casual", "technical", "educational", "friendly"],
            description="Applied personality type"
        ),
        "source_file": DataContractField(
            name="source_file",
            datatype=str,
            required=True,
            min_length=1,
            max_length=255,
            description="Original source file path"
        ),
        "processing_timestamp": DataContractField(
            name="processing_timestamp",
            datatype=str,
            required=True,
            pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
            description="ISO timestamp of processing"
        ),
        "validation_passed": DataContractField(
            name="validation_passed",
            datatype=bool,
            required=True,
            description="Validation status"
        ),
        "tier": DataContractField(
            name="tier",
            datatype=str,
            required=True,
            allowed_values=[t.value for t in QualityTier],
            description="Quality tier classification"
        ),
        "metadata": DataContractField(
            name="metadata",
            datatype=dict,
            required=True,
            description="Additional metadata"
        )
    })
    
    # File-level requirements
    file_requirements: Dict[str, Any] = field(default_factory=lambda: {
        "min_size_bytes": 100,
        "max_size_bytes": 10_000_000,  # 10MB
        "allowed_extensions": [".json", ".jsonl", ".txt"],
        "encoding": "utf-8",
        "max_records_per_file": 10000,
        "required_checksum": True
    })
    
    # Negative examples - what FAILS the contract
    negative_examples: Dict[str, List[str]] = field(default_factory=lambda: {
        "invalid_format": [
            "Random text without proper delimiters",
            "Incomplete conversation missing assistant response",
            "Mixed format types in single record"
        ],
        "quality_failures": [
            "Accuracy score below 95%",
            "Quality score below minimum threshold",
            "Failed validation checks"
        ],
        "content_violations": [
            "Content exceeding 8192 characters",
            "Empty or whitespace-only content",
            "Content with PII or sensitive information"
        ],
        "metadata_failures": [
            "Missing required fields",
            "Invalid timestamp format",
            "Unrecognized personality type"
        ],
        "file_violations": [
            "Files exceeding 10MB size limit",
            "Non-UTF-8 encoding",
            "Missing or invalid checksums"
        ]
    })


class DataContractValidator:
    """Validates data against the perfect data contract."""
    
    def __init__(self, contract: PerfectDataContract):
        self.contract = contract
        
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single data record against the contract.
        
        Returns:
            Dict with validation results and detailed errors
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "contract_version": self.contract.version.value,
            "validated_at": datetime.now().isoformat()
        }
        
        # Check all required fields
        for field_name, field_def in self.contract.required_fields.items():
            if field_name not in record:
                validation_result["errors"].append(f"Missing required field: {field_name}")
                validation_result["is_valid"] = False
                continue
            
            value = record[field_name]
            
            # Type validation
            if not isinstance(value, field_def.datatype):
                validation_result["errors"].append(
                    f"Field {field_name}: Expected {field_def.datatype.__name__}, got {type(value).__name__}"
                )
                validation_result["is_valid"] = False
                continue
            
            # Length validation for strings
            if field_def.datatype == str and value:
                if field_def.min_length and len(value) < field_def.min_length:
                    validation_result["errors"].append(
                        f"Field {field_name}: Length {len(value)} below minimum {field_def.min_length}"
                    )
                    validation_result["is_valid"] = False
                
                if field_def.max_length and len(value) > field_def.max_length:
                    validation_result["errors"].append(
                        f"Field {field_name}: Length {len(value)} exceeds maximum {field_def.max_length}"
                    )
                    validation_result["is_valid"] = False
            
            # Range validation for numbers
            if field_def.datatype in [int, float] and value is not None:
                if field_def.min_length and value < field_def.min_length:
                    validation_result["errors"].append(
                        f"Field {field_name}: Value {value} below minimum {field_def.min_length}"
                    )
                    validation_result["is_valid"] = False
                
                if field_def.max_length and value > field_def.max_length:
                    validation_result["errors"].append(
                        f"Field {field_name}: Value {value} exceeds maximum {field_def.max_length}"
                    )
                    validation_result["is_valid"] = False
            
            # Pattern validation
            if field_def.pattern and field_def.datatype == str:
                if not re.match(field_def.pattern, str(value)):
                    validation_result["errors"].append(
                        f"Field {field_name}: Value '{value}' doesn't match pattern {field_def.pattern}"
                    )
                    validation_result["is_valid"] = False
            
            # Allowed values validation
            if field_def.allowed_values and value not in field_def.allowed_values:
                validation_result["errors"].append(
                    f"Field {field_name}: Value '{value}' not in allowed values {field_def.allowed_values}"
                )
                validation_result["is_valid"] = False
        
        # Critical validation: 95% accuracy requirement
        if "accuracy_score" in record:
            if record["accuracy_score"] < 95.0:
                validation_result["errors"].append(
                    f"CRITICAL: Accuracy score {record['accuracy_score']}% below required 95% minimum"
                )
                validation_result["is_valid"] = False
        
        return validation_result
    
    def validate_file_metadata(self, file_path: str, file_size: int, 
                              checksum: str) -> Dict[str, Any]:
        """Validate file-level requirements."""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Size validation
        if file_size < self.contract.file_requirements["min_size_bytes"]:
            validation_result["errors"].append(
                f"File size {file_size} below minimum {self.contract.file_requirements['min_size_bytes']}"
            )
            validation_result["is_valid"] = False
        
        if file_size > self.contract.file_requirements["max_size_bytes"]:
            validation_result["errors"].append(
                f"File size {file_size} exceeds maximum {self.contract.file_requirements['max_size_bytes']}"
            )
            validation_result["is_valid"] = False
        
        # Extension validation
        file_ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
        if f".{file_ext}" not in self.contract.file_requirements["allowed_extensions"]:
            validation_result["errors"].append(
                f"File extension .{file_ext} not in allowed extensions {self.contract.file_requirements['allowed_extensions']}"
            )
            validation_result["is_valid"] = False
        
        # Checksum validation
        if self.contract.file_requirements["required_checksum"] and not checksum:
            validation_result["errors"].append("Missing required file checksum")
            validation_result["is_valid"] = False
        
        return validation_result


def get_perfect_data_contract() -> PerfectDataContract:
    """Get the current immutable data contract."""
    return PerfectDataContract()


def create_contract_documentation() -> str:
    """Generate comprehensive contract documentation."""
    contract = get_perfect_data_contract()
    
    doc = f"""
# PERFECT DATA CONTRACT - VERSION {contract.version.value}
## IMMUTABLE SPECIFICATION - TEAM SIGN-OFF REQUIRED FOR CHANGES

### REQUIRED FIELDS
"""
    
    for field_name, field_def in contract.required_fields.items():
        doc += f"""
**{field_name}** ({field_def.datatype.__name__})
- Required: {field_def.required}
- Description: {field_def.description}
"""
        if field_def.min_length is not None:
            doc += f"- Min: {field_def.min_length}\n"
        if field_def.max_length is not None:
            doc += f"- Max: {field_def.max_length}\n"
        if field_def.pattern:
            doc += f"- Pattern: {field_def.pattern}\n"
        if field_def.allowed_values:
            doc += f"- Allowed Values: {field_def.allowed_values}\n"
    
    doc += f"""
### NEGATIVE EXAMPLES - CONTRACT FAILURES
"""
    
    for category, examples in contract.negative_examples.items():
        doc += f"""
**{category.upper()}:**
"""
        for example in examples:
            doc += f"- {example}\n"
    
    return doc


if __name__ == "__main__":
    # Generate contract documentation
    contract = get_perfect_data_contract()
    validator = DataContractValidator(contract)
    
    print("📋 PERFECT DATA CONTRACT")
    print("=" * 50)
    print(f"Version: {contract.version.value}")
    print(f"Required Fields: {len(contract.required_fields)}")
    print(f"File Requirements: {len(contract.file_requirements)}")
    print(f"Negative Examples: {sum(len(examples) for examples in contract.negative_examples.values())}")
    
    # Save documentation
    with open("DATA_CONTRACT_SPECIFICATION.md", "w") as f:
        f.write(create_contract_documentation())
    
    print("✅ Contract documentation generated: DATA_CONTRACT_SPECIFICATION.md")
