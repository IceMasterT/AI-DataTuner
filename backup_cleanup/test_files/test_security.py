#!/usr/bin/env python3
"""
Simple test script for the security system.
"""

from sanitization_engine import CoreSanitizer, ThreatLevel
from security_config import SecurityConfigManager, SecurityLevel


def test_basic_sanitization():
    """Test basic sanitization functionality."""
    print("Testing basic sanitization...")
    
    sanitizer = CoreSanitizer()
    
    # Test clean text
    clean_text = "What is machine learning? Machine learning is a subset of AI."
    result = sanitizer.sanitize_text(clean_text)
    
    print(f"Clean text result: {result.threat_level}")
    assert result.threat_level == ThreatLevel.CLEAN
    
    # Test invisible characters
    invisible_text = "What is AI?\u200B\u200C Hidden content"
    result = sanitizer.sanitize_text(invisible_text)
    
    print(f"Invisible chars result: {result.threat_level}")
    assert len(result.threats_detected) > 0
    
    print("✓ Basic sanitization tests passed")


def test_security_config():
    """Test security configuration."""
    print("Testing security configuration...")
    
    config_manager = SecurityConfigManager()
    
    # Test loading different security levels
    for level in SecurityLevel:
        config_manager.load_security_level(level)
        print(f"✓ Loaded {level.value} security level")
    
    # Test configuration validation
    issues = config_manager.validate_config()
    print(f"Configuration issues: {len(issues)}")
    
    print("✓ Security configuration tests passed")


def main():
    """Run basic tests."""
    print("🛡️ SECURITY SYSTEM BASIC TESTS")
    print("=" * 40)
    
    try:
        test_basic_sanitization()
        test_security_config()
        
        print("\n🎉 All basic tests passed!")
        print("The security system is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
