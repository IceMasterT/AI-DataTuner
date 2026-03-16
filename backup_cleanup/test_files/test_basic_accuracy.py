#!/usr/bin/env python3
"""
Basic test for enhanced accuracy system functionality.
"""

def test_strict_prompting():
    """Test strict prompting system."""
    print("🔍 Testing Strict Prompting System")
    
    try:
        from strict_prompting_system import StrictPromptingSystem
        
        # Initialize system
        prompting_system = StrictPromptingSystem(max_attempts=2, target_accuracy=95.0)
        print("✅ Strict prompting system initialized")
        
        # Test content
        test_content = "Machine learning is a method of data analysis that automates analytical model building."
        
        # Test formatting
        result = prompting_system.format_with_strict_prompting(
            test_content, "qwen", "professional"
        )
        
        print(f"📊 Results:")
        print(f"   Accuracy Score: {result.accuracy_score:.1f}%")
        print(f"   Validation Passed: {result.validation_passed}")
        print(f"   Attempts Used: {result.attempts_used}")
        print(f"   Processing Time: {result.processing_time:.2f}s")
        
        # Show formatted content
        print(f"📝 Formatted Content:")
        print(result.formatted_content[:300] + "..." if len(result.formatted_content) > 300 else result.formatted_content)
        
        if result.accuracy_score >= 95.0:
            print("✅ SUCCESS: Meets 95% accuracy target")
            return True
        else:
            print(f"❌ BELOW TARGET: {result.accuracy_score:.1f}% accuracy")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_conversation_formatter():
    """Test basic conversation formatter."""
    print("\n🔍 Testing Conversation Formatter")
    
    try:
        from conversation_formatter import ConversationFormatter
        
        # Initialize formatter
        formatter = ConversationFormatter("qwen")
        print("✅ Conversation formatter initialized")
        
        # Test formatting
        result = formatter.format_conversation(
            "What is machine learning?",
            "Machine learning is a method of data analysis that automates analytical model building."
        )
        
        print(f"📊 Results:")
        print(f"   Success: {result.success}")
        print(f"   Format Type: {result.format_type}")
        
        if result.success:
            print(f"📝 Formatted Content:")
            print(result.formatted_content)
            print("✅ SUCCESS: Basic formatting works")
            return True
        else:
            print(f"❌ FAILED: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_enhanced_accuracy_basic():
    """Test basic enhanced accuracy functionality."""
    print("\n🔍 Testing Enhanced Accuracy System (Basic)")
    
    try:
        from enhanced_accuracy_system import EnhancedAccuracySystem
        
        # Initialize system
        accuracy_system = EnhancedAccuracySystem(target_accuracy=95.0)
        print("✅ Enhanced accuracy system initialized")
        
        # Test content
        test_content = """<|user|>
What is machine learning?
<|assistant|>
Machine learning is a method of data analysis that automates analytical model building.
"""
        
        original_content = "Machine learning is a method of data analysis that automates analytical model building."
        
        # Test validation
        result = accuracy_system.validate_and_enhance(
            test_content, "qwen", original_content
        )
        
        print(f"📊 Results:")
        print(f"   Accuracy Score: {result.accuracy_score:.1f}%")
        print(f"   Validation Passed: {result.is_valid}")
        print(f"   Errors: {len(result.errors)}")
        print(f"   Corrections: {len(result.corrections)}")
        
        if result.accuracy_score >= 80.0:  # Lower threshold for basic test
            print("✅ SUCCESS: Basic accuracy validation works")
            return True
        else:
            print(f"❌ BELOW THRESHOLD: {result.accuracy_score:.1f}% accuracy")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_quality_scorer_basic():
    """Test basic quality scorer functionality."""
    print("\n🔍 Testing Quality Scorer (Basic)")
    
    try:
        from quality_scorer import LLMQualityScorer
        
        # Initialize scorer
        scorer = LLMQualityScorer(target_accuracy=95.0)
        print("✅ Quality scorer initialized")
        
        # Test content
        test_content = """<|user|>
What is machine learning?
<|assistant|>
Machine learning is a method of data analysis that automates analytical model building.
"""
        
        # Test scoring
        score = scorer.score_content(test_content)
        
        print(f"📊 Results:")
        print(f"   Overall Score: {score.overall_score:.1f}%")
        print(f"   Accuracy Score: {score.accuracy_score:.1f}%")
        print(f"   Confidence: {score.confidence:.2f}")
        
        if score.overall_score >= 50.0:  # Lower threshold for basic test
            print("✅ SUCCESS: Basic quality scoring works")
            return True
        else:
            print(f"❌ LOW SCORE: {score.overall_score:.1f}%")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Run basic tests."""
    print("🧪 BASIC ACCURACY SYSTEM TEST")
    print("Testing core functionality of enhanced accuracy components")
    
    tests = [
        ("Strict Prompting System", test_strict_prompting),
        ("Conversation Formatter", test_conversation_formatter),
        ("Enhanced Accuracy System", test_enhanced_accuracy_basic),
        ("Quality Scorer", test_quality_scorer_basic)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    print("\n" + "="*60)
    print(" TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL BASIC TESTS PASSED!")
        print("✅ Core enhanced accuracy system components are functional")
        return 0
    else:
        print(f"\n❌ {total-passed} TESTS FAILED!")
        print("Please review the failed components")
        return 1

if __name__ == "__main__":
    exit(main())
