#!/usr/bin/env python3
"""
Security configuration and customization system for the sanitization pipeline.
Provides configurable filtering rules, thresholds, and sanitization options.
"""

import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class SecurityLevel(Enum):
    """Security levels for different use cases."""
    PERMISSIVE = "permissive"
    BALANCED = "balanced"
    STRICT = "strict"
    PARANOID = "paranoid"


@dataclass
class SanitizationConfig:
    """Configuration for sanitization behavior."""
    # Core sanitization settings
    unicode_normalization: bool = True
    remove_invisible_chars: bool = True
    normalize_homoglyphs: bool = True
    
    # Threat detection thresholds
    entropy_low_threshold: float = 2.0
    entropy_high_threshold: float = 7.0
    non_ascii_ratio_threshold: float = 0.5
    repetition_threshold: float = 0.3
    
    # Advanced detection settings
    enable_advanced_detection: bool = True
    homoglyph_detection_sensitivity: float = 0.1
    script_mixing_tolerance: bool = False
    
    # Markup validation settings
    validate_html: bool = True
    validate_json: bool = True
    validate_xml: bool = True
    validate_markdown: bool = True
    validate_code: bool = True
    
    # Action thresholds
    quarantine_threshold_score: float = 30.0
    rejection_threshold_score: float = 60.0
    
    # Quarantine settings
    enable_quarantine: bool = True
    quarantine_retention_days: int = 90
    auto_cleanup_approved: bool = True


@dataclass
class FilteringRules:
    """Configurable filtering rules."""
    # Content length limits
    min_content_length: int = 10
    max_content_length: int = 1000000

    # Blocked patterns
    blocked_patterns: List[str] = None

    # Allowed patterns (whitelist)
    allowed_patterns: List[str] = None

    # Suspicious keywords
    suspicious_keywords: List[str] = None

    # File type restrictions
    allowed_file_extensions: List[str] = None
    blocked_file_extensions: List[str] = None

    # Language restrictions
    allowed_scripts: List[str] = None
    blocked_scripts: List[str] = None

    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.blocked_patterns is None:
            self.blocked_patterns = []
        if self.allowed_patterns is None:
            self.allowed_patterns = []
        if self.suspicious_keywords is None:
            self.suspicious_keywords = []
        if self.allowed_file_extensions is None:
            self.allowed_file_extensions = []
        if self.blocked_file_extensions is None:
            self.blocked_file_extensions = []
        if self.allowed_scripts is None:
            self.allowed_scripts = []
        if self.blocked_scripts is None:
            self.blocked_scripts = []


class SecurityConfigManager:
    """Manages security configuration and profiles."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Default configurations for different security levels
        self.default_configs = self._create_default_configs()
        
        # Current active configuration
        self.active_config = self.default_configs[SecurityLevel.BALANCED]
        self.active_rules = self._create_default_rules()
    
    def _create_default_configs(self) -> Dict[SecurityLevel, SanitizationConfig]:
        """Create default configurations for different security levels."""
        configs = {}
        
        # Permissive configuration
        configs[SecurityLevel.PERMISSIVE] = SanitizationConfig(
            unicode_normalization=True,
            remove_invisible_chars=True,
            normalize_homoglyphs=False,
            entropy_low_threshold=1.0,
            entropy_high_threshold=8.0,
            non_ascii_ratio_threshold=0.8,
            repetition_threshold=0.5,
            enable_advanced_detection=False,
            homoglyph_detection_sensitivity=0.3,
            script_mixing_tolerance=True,
            validate_html=False,
            validate_json=True,
            validate_xml=False,
            validate_markdown=False,
            validate_code=False,
            quarantine_threshold_score=50.0,
            rejection_threshold_score=80.0,
            enable_quarantine=True,
            quarantine_retention_days=30,
            auto_cleanup_approved=True
        )
        
        # Balanced configuration (default)
        configs[SecurityLevel.BALANCED] = SanitizationConfig(
            unicode_normalization=True,
            remove_invisible_chars=True,
            normalize_homoglyphs=True,
            entropy_low_threshold=2.0,
            entropy_high_threshold=7.0,
            non_ascii_ratio_threshold=0.5,
            repetition_threshold=0.3,
            enable_advanced_detection=True,
            homoglyph_detection_sensitivity=0.1,
            script_mixing_tolerance=False,
            validate_html=True,
            validate_json=True,
            validate_xml=True,
            validate_markdown=True,
            validate_code=True,
            quarantine_threshold_score=30.0,
            rejection_threshold_score=60.0,
            enable_quarantine=True,
            quarantine_retention_days=90,
            auto_cleanup_approved=True
        )
        
        # Strict configuration
        configs[SecurityLevel.STRICT] = SanitizationConfig(
            unicode_normalization=True,
            remove_invisible_chars=True,
            normalize_homoglyphs=True,
            entropy_low_threshold=2.5,
            entropy_high_threshold=6.5,
            non_ascii_ratio_threshold=0.3,
            repetition_threshold=0.2,
            enable_advanced_detection=True,
            homoglyph_detection_sensitivity=0.05,
            script_mixing_tolerance=False,
            validate_html=True,
            validate_json=True,
            validate_xml=True,
            validate_markdown=True,
            validate_code=True,
            quarantine_threshold_score=20.0,
            rejection_threshold_score=40.0,
            enable_quarantine=True,
            quarantine_retention_days=180,
            auto_cleanup_approved=False
        )
        
        # Paranoid configuration
        configs[SecurityLevel.PARANOID] = SanitizationConfig(
            unicode_normalization=True,
            remove_invisible_chars=True,
            normalize_homoglyphs=True,
            entropy_low_threshold=3.0,
            entropy_high_threshold=6.0,
            non_ascii_ratio_threshold=0.1,
            repetition_threshold=0.1,
            enable_advanced_detection=True,
            homoglyph_detection_sensitivity=0.01,
            script_mixing_tolerance=False,
            validate_html=True,
            validate_json=True,
            validate_xml=True,
            validate_markdown=True,
            validate_code=True,
            quarantine_threshold_score=10.0,
            rejection_threshold_score=25.0,
            enable_quarantine=True,
            quarantine_retention_days=365,
            auto_cleanup_approved=False
        )
        
        return configs
    
    def _create_default_rules(self) -> FilteringRules:
        """Create default filtering rules."""
        return FilteringRules(
            blocked_patterns=[
                r'<script[^>]*>.*?</script>',
                r'javascript:',
                r'eval\s*\(',
                r'document\.write',
                r'innerHTML\s*=',
                r';\s*DROP\s+TABLE',
                r'UNION\s+SELECT',
                r'<iframe[^>]*>',
                r'<object[^>]*>',
                r'<embed[^>]*>',
            ],
            allowed_patterns=[
                r'^[a-zA-Z0-9\s\.,!?\-_]+$',  # Basic alphanumeric with punctuation
            ],
            suspicious_keywords=[
                'eval', 'exec', 'compile', 'import', '__import__',
                'script', 'iframe', 'object', 'embed', 'form',
                'onclick', 'onload', 'onerror', 'javascript',
                'vbscript', 'data:', 'file://', 'ftp://',
                'drop table', 'delete from', 'union select',
                'xss', 'csrf', 'injection', 'payload'
            ],
            allowed_file_extensions=[
                '.txt', '.md', '.json', '.csv', '.tsv',
                '.xml', '.html', '.htm', '.yaml', '.yml'
            ],
            blocked_file_extensions=[
                '.exe', '.bat', '.cmd', '.scr', '.com',
                '.pif', '.vbs', '.js', '.jar', '.app'
            ],
            min_content_length=10,
            max_content_length=1000000,
            allowed_scripts=[
                'LATIN', 'COMMON', 'INHERITED'
            ],
            blocked_scripts=[
                'UNKNOWN', 'UNASSIGNED'
            ]
        )
    
    def load_security_level(self, level: SecurityLevel):
        """Load a predefined security level configuration."""
        if level in self.default_configs:
            self.active_config = self.default_configs[level]
        else:
            raise ValueError(f"Unknown security level: {level}")
    
    def load_config_from_file(self, config_file: str) -> bool:
        """Load configuration from file."""
        config_path = Path(config_file)
        
        if not config_path.exists():
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)
            
            # Load sanitization config
            if 'sanitization' in config_data:
                self.active_config = SanitizationConfig(**config_data['sanitization'])
            
            # Load filtering rules
            if 'filtering_rules' in config_data:
                self.active_rules = FilteringRules(**config_data['filtering_rules'])
            
            return True
        except Exception as e:
            print(f"Error loading config: {e}")
            return False
    
    def save_config_to_file(self, config_file: str, format: str = "yaml") -> bool:
        """Save current configuration to file."""
        config_path = Path(config_file)
        
        try:
            config_data = {
                'sanitization': asdict(self.active_config),
                'filtering_rules': asdict(self.active_rules)
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                if format.lower() in ['yaml', 'yml']:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def update_config(self, **kwargs):
        """Update specific configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self.active_config, key):
                setattr(self.active_config, key, value)
    
    def update_rules(self, **kwargs):
        """Update specific filtering rules."""
        for key, value in kwargs.items():
            if hasattr(self.active_rules, key):
                setattr(self.active_rules, key, value)
    
    def add_blocked_pattern(self, pattern: str):
        """Add a new blocked pattern."""
        if pattern not in self.active_rules.blocked_patterns:
            self.active_rules.blocked_patterns.append(pattern)
    
    def remove_blocked_pattern(self, pattern: str):
        """Remove a blocked pattern."""
        if pattern in self.active_rules.blocked_patterns:
            self.active_rules.blocked_patterns.remove(pattern)
    
    def add_suspicious_keyword(self, keyword: str):
        """Add a new suspicious keyword."""
        if keyword not in self.active_rules.suspicious_keywords:
            self.active_rules.suspicious_keywords.append(keyword)
    
    def remove_suspicious_keyword(self, keyword: str):
        """Remove a suspicious keyword."""
        if keyword in self.active_rules.suspicious_keywords:
            self.active_rules.suspicious_keywords.remove(keyword)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration."""
        return {
            'sanitization_config': asdict(self.active_config),
            'filtering_rules': {
                'blocked_patterns_count': len(self.active_rules.blocked_patterns),
                'allowed_patterns_count': len(self.active_rules.allowed_patterns),
                'suspicious_keywords_count': len(self.active_rules.suspicious_keywords),
                'content_length_limits': {
                    'min': self.active_rules.min_content_length,
                    'max': self.active_rules.max_content_length
                }
            }
        }
    
    def validate_config(self) -> List[str]:
        """Validate current configuration and return any issues."""
        issues = []
        
        # Check threshold consistency
        if self.active_config.entropy_low_threshold >= self.active_config.entropy_high_threshold:
            issues.append("Low entropy threshold must be less than high entropy threshold")
        
        if self.active_config.quarantine_threshold_score >= self.active_config.rejection_threshold_score:
            issues.append("Quarantine threshold must be less than rejection threshold")
        
        # Check value ranges
        if not (0.0 <= self.active_config.non_ascii_ratio_threshold <= 1.0):
            issues.append("Non-ASCII ratio threshold must be between 0.0 and 1.0")
        
        if not (0.0 <= self.active_config.repetition_threshold <= 1.0):
            issues.append("Repetition threshold must be between 0.0 and 1.0")
        
        if not (0.0 <= self.active_config.homoglyph_detection_sensitivity <= 1.0):
            issues.append("Homoglyph detection sensitivity must be between 0.0 and 1.0")
        
        # Check content length limits
        if self.active_rules.min_content_length >= self.active_rules.max_content_length:
            issues.append("Minimum content length must be less than maximum content length")
        
        return issues
    
    def create_custom_profile(self, profile_name: str, base_level: SecurityLevel = SecurityLevel.BALANCED) -> bool:
        """Create a custom security profile based on existing level."""
        try:
            profile_path = self.config_dir / f"{profile_name}.yaml"
            
            # Start with base configuration
            base_config = self.default_configs[base_level]
            
            config_data = {
                'profile_name': profile_name,
                'base_level': base_level.value,
                'sanitization': asdict(base_config),
                'filtering_rules': asdict(self.active_rules)
            }
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error creating custom profile: {e}")
            return False
    
    def list_available_profiles(self) -> List[str]:
        """List all available configuration profiles."""
        profiles = []
        
        # Add built-in security levels
        for level in SecurityLevel:
            profiles.append(f"builtin:{level.value}")
        
        # Add custom profiles
        for config_file in self.config_dir.glob("*.yaml"):
            profiles.append(f"custom:{config_file.stem}")
        
        return profiles
    
    def export_config_template(self, template_file: str) -> bool:
        """Export a configuration template with comments."""
        template_content = """# Security Configuration Template
# This file contains all available configuration options with explanations

# Sanitization Configuration
sanitization:
  # Unicode normalization (recommended: true)
  unicode_normalization: true
  
  # Remove invisible characters (recommended: true)
  remove_invisible_chars: true
  
  # Normalize homoglyphs to prevent lookalike attacks (recommended: true)
  normalize_homoglyphs: true
  
  # Entropy thresholds for detecting random/repetitive content
  entropy_low_threshold: 2.0   # Below this = too repetitive
  entropy_high_threshold: 7.0  # Above this = too random
  
  # Ratio of non-ASCII characters that triggers suspicion (0.0-1.0)
  non_ascii_ratio_threshold: 0.5
  
  # Character repetition threshold (0.0-1.0)
  repetition_threshold: 0.3
  
  # Enable advanced threat detection algorithms
  enable_advanced_detection: true
  
  # Homoglyph detection sensitivity (0.0-1.0, lower = more sensitive)
  homoglyph_detection_sensitivity: 0.1
  
  # Allow mixing of different writing scripts
  script_mixing_tolerance: false
  
  # Markup validation settings
  validate_html: true
  validate_json: true
  validate_xml: true
  validate_markdown: true
  validate_code: true
  
  # Action thresholds (threat scores)
  quarantine_threshold_score: 30.0  # Quarantine above this score
  rejection_threshold_score: 60.0   # Reject above this score
  
  # Quarantine system settings
  enable_quarantine: true
  quarantine_retention_days: 90
  auto_cleanup_approved: true

# Filtering Rules
filtering_rules:
  # Patterns that are always blocked (regex)
  blocked_patterns:
    - '<script[^>]*>.*?</script>'
    - 'javascript:'
    - 'eval\\s*\\('
  
  # Patterns that are always allowed (regex)
  allowed_patterns:
    - '^[a-zA-Z0-9\\s\\.,!?\\-_]+$'
  
  # Keywords that raise suspicion
  suspicious_keywords:
    - 'eval'
    - 'exec'
    - 'script'
    - 'injection'
  
  # File extension restrictions
  allowed_file_extensions:
    - '.txt'
    - '.md'
    - '.json'
  
  blocked_file_extensions:
    - '.exe'
    - '.bat'
    - '.js'
  
  # Content length limits
  min_content_length: 10
  max_content_length: 1000000
  
  # Unicode script restrictions
  allowed_scripts:
    - 'LATIN'
    - 'COMMON'
  
  blocked_scripts:
    - 'UNKNOWN'
"""
        
        try:
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(template_content)
            return True
        except Exception as e:
            print(f"Error exporting template: {e}")
            return False
