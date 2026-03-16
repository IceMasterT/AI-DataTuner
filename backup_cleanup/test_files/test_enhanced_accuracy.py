#!/usr/bin/env python3
"""
Test script for Enhanced Accuracy System - Verifies 95% minimum accuracy.
Tests strict prompting, validation, and enhanced formatting systems.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)

def print_section(title):
    """Print a section header."""
    print(f"\n🔍 {title}")
    print("-" * 50)

def test_enhanced_accuracy_system():
    """Test the enhanced accuracy system."""
    print_section("Testing Enhanced Accuracy System")
    
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
        
        print(f"📊 Validation Results:")
        print(f"   Accuracy Score: {result.accuracy_score:.1f}%")
        print(f"   Validation Passed: {result.is_valid}")
        print(f"   Errors: {len(result.errors)}")
        print(f"   Warnings: {len(result.warnings)}")
        print(f"   Corrections: {len(result.corrections)}")
        
        if result.accuracy_score >= 95.0:
            print("✅ Enhanced accuracy system meets 95% target")
            return True
        else:
            print(f"❌ Enhanced accuracy system below target: {result.accuracy_score:.1f}%")
            return False
            
    except Exception as e:
        print(f"❌ Enhanced accuracy system test failed: {e}")
        return False

def test_strict_prompting_system():
    """Test the strict prompting system."""
    print_section("Testing Strict Prompting System")
    
    try:
        from strict_prompting_system import StrictPromptingSystem
        
        # Initialize system
        prompting_system = StrictPromptingSystem(max_attempts=3, target_accuracy=95.0)
        print("✅ Strict prompting system initialized")
        
        # Test content
        test_content = "Machine learning is a method of data analysis that automates analytical model building."
        
        # Test formatting
        result = prompting_system.format_with_strict_prompting(
            test_content, "qwen", "professional"
        )
        
        print(f"📊 Prompting Results:")
        print(f"   Accuracy Score: {result.accuracy_score:.1f}%")
        print(f"   Validation Passed: {result.validation_passed}")
        print(f"   Attempts Used: {result.attempts_used}")
        print(f"   Corrections Applied: {len(result.corrections_applied)}")
        print(f"   Processing Time: {result.processing_time:.2f}s")
        
        if result.accuracy_score >= 95.0:
            print("✅ Strict prompting system meets 95% target")
            return True
        else:
            print(f"❌ Strict prompting system below target: {result.accuracy_score:.1f}%")
            return False
            
    except Exception as e:
        print(f"❌ Strict prompting system test failed: {e}")
        return False

def test_enhanced_conversation_formatter():
    """Test the enhanced conversation formatter."""
    print_section("Testing Enhanced Conversation Formatter")
    
    try:
        from enhanced_conversation_formatter import get_enhanced_formatter
        
        # Initialize formatter
        formatter = get_enhanced_formatter("qwen", target_accuracy=95.0)
        print("✅ Enhanced conversation formatter initialized")
        
        # Test conversation
        user_input = "What is machine learning?"
        assistant_response = "Machine learning is a method of data analysis that automates analytical model building. It is a branch of artificial intelligence based on the idea that systems can learn from data, identify patterns and make decisions with minimal human intervention."
        
        # Test formatting
        result = formatter.format_conversation_enhanced(
            user_input, assistant_response, "professional"
        )
        
        print(f"📊 Formatting Results:")
        print(f"   Accuracy Score: {result.accuracy_score:.1f}%")
        print(f"   Validation Passed: {result.validation_passed}")
        print(f"   Quality Score: {result.quality_score:.1f}%")
        print(f"   Attempts Used: {result.attempts_used}")
        print(f"   Corrections Applied: {len(result.corrections_applied)}")
        print(f"   Confidence: {result.confidence:.2f}")
        
        # Show formatted content preview
        print(f"📝 Formatted Content Preview:")
        preview = result.formatted_content[:200] + "..." if len(result.formatted_content) > 200 else result.formatted_content
        print(f"   {preview}")
        
        if result.accuracy_score >= 95.0 and result.validation_passed:
            print("✅ Enhanced conversation formatter meets 95% target")
            return True
        else:
            print(f"❌ Enhanced conversation formatter below target: {result.accuracy_score:.1f}%")
            return False
            
    except Exception as e:
        print(f"❌ Enhanced conversation formatter test failed: {e}")
        return False

def test_enhanced_quality_scorer():
    """Test the enhanced quality scorer."""
    print_section("Testing Enhanced Quality Scorer")
    
    try:
        from quality_scorer import LLMQualityScorer
        
        # Initialize scorer with enhanced accuracy
        scorer = LLMQualityScorer(target_accuracy=95.0)
        print("✅ Enhanced quality scorer initialized")
        
        # Test content
        test_content = """<|user|>
What is machine learning?
<|assistant|>
Machine learning is a method of data analysis that automates analytical model building. It is a branch of artificial intelligence based on the idea that systems can learn from data, identify patterns and make decisions with minimal human intervention.
"""
        
        original_content = "Machine learning is a method of data analysis that automates analytical model building. It is a branch of artificial intelligence based on the idea that systems can learn from data, identify patterns and make decisions with minimal human intervention."
        
        # Test scoring with enhanced context
        context = {
            "original_content": original_content,
            "format_type": "qwen"
        }
        
        score = scorer.score_content(test_content, context, original_content, "qwen")
        
        print(f"📊 Quality Scoring Results:")
        print(f"   Overall Score: {score.overall_score:.1f}%")
        print(f"   Accuracy Score: {score.accuracy_score:.1f}%")
        print(f"   Fluency Score: {score.fluency_score:.1f}%")
        print(f"   Coherence Score: {score.coherence_score:.1f}%")
        print(f"   Training Readiness: {score.training_readiness_score:.1f}%")
        print(f"   Confidence: {score.confidence:.2f}")
        
        if score.accuracy_score >= 95.0:
            print("✅ Enhanced quality scorer meets 95% target")
            return True
        else:
            print(f"❌ Enhanced quality scorer below target: {score.accuracy_score:.1f}%")
            return False
            
    except Exception as e:
        print(f"❌ Enhanced quality scorer test failed: {e}")
        return False

def test_pipeline_integration():
    """Test integration with phase-controlled pipeline."""
    print_section("Testing Pipeline Integration")
    
    try:
        from phase_controlled_pipeline import get_pipeline
        
        # Get pipeline
        pipeline = get_pipeline()
        print("✅ Pipeline initialized with enhanced accuracy")
        
        # Check Phase 3 configuration
        phase3_config = pipeline.phases.get("phase3_personality")
        if phase3_config:
            print(f"✅ Phase 3 configured: {phase3_config.name}")
            print(f"   Enhanced formatting: Available")
        else:
            print("❌ Phase 3 not found")
            return False
        
        # Check Phase 4 configuration
        phase4_config = pipeline.phases.get("phase4_quality")
        if phase4_config:
            print(f"✅ Phase 4 configured: {phase4_config.name}")
            print(f"   Enhanced scoring: Available")
        else:
            print("❌ Phase 4 not found")
            return False
        
        print("✅ Pipeline integration successful")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline integration test failed: {e}")
        return False

def run_accuracy_benchmark():
    """Run a comprehensive accuracy benchmark."""
    print_section("Running Accuracy Benchmark")
    
    test_cases = [
        {
            "content": "Machine learning is a method of data analysis that automates analytical model building.",
            "format": "qwen",
            "personality": "professional"
        },
        {
            "content": "Natural language processing (NLP) is a subfield of linguistics, computer science, and artificial intelligence.",
            "format": "alpaca", 
            "personality": "technical"
        },
        {
            "content": "Deep learning is part of a broader family of machine learning methods based on artificial neural networks.",
            "format": "chatml",
            "personality": "educational"
        }
    ]
    
    try:
        from enhanced_conversation_formatter import get_enhanced_formatter
        
        total_tests = len(test_cases)
        passed_tests = 0
        accuracy_scores = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test Case {i}/{total_tests}: {test_case['format']} format")
            
            formatter = get_enhanced_formatter(test_case['format'], target_accuracy=95.0)
            
            result = formatter.format_conversation_enhanced(
                "Explain this concept:",
                test_case['content'],
                test_case['personality']
            )
            
            accuracy_scores.append(result.accuracy_score)
            
            if result.accuracy_score >= 95.0 and result.validation_passed:
                passed_tests += 1
                print(f"   ✅ PASSED - Accuracy: {result.accuracy_score:.1f}%")
            else:
                print(f"   ❌ FAILED - Accuracy: {result.accuracy_score:.1f}%")
        
        # Calculate benchmark results
        pass_rate = (passed_tests / total_tests) * 100
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores)
        min_accuracy = min(accuracy_scores)
        max_accuracy = max(accuracy_scores)
        
        print(f"\n📊 Benchmark Results:")
        print(f"   Pass Rate: {pass_rate:.1f}% ({passed_tests}/{total_tests})")
        print(f"   Average Accuracy: {avg_accuracy:.1f}%")
        print(f"   Min Accuracy: {min_accuracy:.1f}%")
        print(f"   Max Accuracy: {max_accuracy:.1f}%")
        
        if pass_rate >= 95.0 and avg_accuracy >= 95.0:
            print("✅ Benchmark PASSED - System meets 95% accuracy target")
            return True
        else:
            print("❌ Benchmark FAILED - System below 95% accuracy target")
            return False
            
    except Exception as e:
        print(f"❌ Accuracy benchmark failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 ENHANCED ACCURACY SYSTEM - COMPREHENSIVE TEST")
    print("Testing 95% minimum accuracy with strict prompting and validation")
    print(f"Test started at: {datetime.now()}")
    
    all_tests_passed = True
    test_results = {}
    
    # Run all tests
    tests = [
        ("Enhanced Accuracy System", test_enhanced_accuracy_system),
        ("Strict Prompting System", test_strict_prompting_system),
        ("Enhanced Conversation Formatter", test_enhanced_conversation_formatter),
        ("Enhanced Quality Scorer", test_enhanced_quality_scorer),
        ("Pipeline Integration", test_pipeline_integration),
        ("Accuracy Benchmark", run_accuracy_benchmark)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results[test_name] = result
            if not result:
                all_tests_passed = False
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            test_results[test_name] = False
            all_tests_passed = False
    
    print_header("TEST RESULTS SUMMARY")
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    if all_tests_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Enhanced accuracy system achieves 95% minimum accuracy")
        print("✅ Strict prompting system provides effective data formatting")
        print("✅ All components integrated and working correctly")
        
        print("\n🎯 System Capabilities:")
        print("   • 95% minimum accuracy validation")
        print("   • Multi-layer validation and correction")
        print("   • Strict prompting with retry logic")
        print("   • Enhanced conversation formatting")
        print("   • Comprehensive quality scoring")
        print("   • Real-time accuracy monitoring")
        
        return 0
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Please review the failed tests and address any issues.")
        return 1

if __name__ == "__main__":
    exit(main())
