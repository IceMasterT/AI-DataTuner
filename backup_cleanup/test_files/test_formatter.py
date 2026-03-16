#!/usr/bin/env python3
"""
Test script for the Text Formatter application.
"""

import unittest
import tempfile
import os
from pathlib import Path
from text_formatter import ConversationFormatter, AdvancedTextClassifier
from utils import (
    preprocess_text, split_text_intelligently, score_as_question, 
    score_as_answer, validate_input
)


class TestTextClassifier(unittest.TestCase):
    """Test the AdvancedTextClassifier."""
    
    def setUp(self):
        self.classifier = AdvancedTextClassifier()
    
    def test_question_classification(self):
        """Test question classification."""
        questions = [
            "What is the role of the ATGS 3000 in astrology?",
            "How do I use astrology to make important decisions?",
            "Can you explain the difference between Western and Vedic astrology?",
            "Why is this important?",
            "Where can I find more information?"
        ]
        
        for question in questions:
            result = self.classifier.classify_text(question)
            self.assertEqual(result, "user", f"Failed to classify as question: {question}")
    
    def test_answer_classification(self):
        """Test answer classification."""
        answers = [
            "The ATGS 3000 is a breakthrough tool for manifesting astrological trends.",
            "Your chart reveals the best timing for major life events.",
            "Western astrology is based on the tropical zodiac and focuses on the sun's position.",
            "According to research, this method is highly effective.",
            "Based on studies, the results show significant improvement."
        ]
        
        for answer in answers:
            result = self.classifier.classify_text(answer)
            self.assertEqual(result, "assistant", f"Failed to classify as answer: {answer}")


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def test_preprocess_text(self):
        """Test text preprocessing."""
        raw_text = "  This is   a test.   Another sentence.  "
        processed = preprocess_text(raw_text)
        self.assertEqual(processed, "This is a test. Another sentence.")
    
    def test_split_text_intelligently(self):
        """Test intelligent text splitting."""
        text = "First paragraph.\n\nSecond paragraph. This is a long sentence that should be kept together."
        segments = split_text_intelligently(text)
        self.assertGreater(len(segments), 1)
        self.assertTrue(all(len(seg.strip()) > 0 for seg in segments))
    
    def test_question_scoring(self):
        """Test question scoring."""
        question = "What is machine learning?"
        score = score_as_question(question)
        self.assertGreater(score, 0.5)
        
        statement = "Machine learning is a subset of AI."
        score = score_as_question(statement)
        self.assertLess(score, 0.5)
    
    def test_answer_scoring(self):
        """Test answer scoring."""
        answer = "Machine learning is a subset of artificial intelligence."
        score = score_as_answer(answer)
        self.assertGreater(score, 0.3)
        
        question = "What is machine learning?"
        score = score_as_answer(question)
        self.assertLess(score, 0.3)
    
    def test_input_validation(self):
        """Test input validation."""
        # Valid input
        valid_text = "This is a valid text with sufficient length."
        is_valid, error = validate_input(valid_text)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        
        # Invalid input - empty
        is_valid, error = validate_input("")
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())
        
        # Invalid input - too short
        is_valid, error = validate_input("short")
        self.assertFalse(is_valid)
        self.assertIn("short", error.lower())


class TestConversationFormatter(unittest.TestCase):
    """Test the ConversationFormatter."""
    
    def setUp(self):
        self.formatter = ConversationFormatter()
    
    def test_process_sample_text(self):
        """Test processing of sample text."""
        sample_text = """What is the role of the ATGS 3000 in astrology? The ATGS 3000 is a breakthrough tool for manifesting astrological trends. With this technology, you can create and direct any astrological energy field—even those that never occur naturally—toward your personal goals.

How do I use astrology to make important decisions? Your chart reveals the best timing for major life events. By observing planetary transits and consulting with an astrologer, you can choose periods when cosmic energies support your plans."""
        
        result = self.formatter.process_text(sample_text)
        
        # Check that result contains proper formatting
        self.assertIn("<|user|>", result)
        self.assertIn("<|assistant|>", result)
        
        # Check that questions are classified as user
        self.assertIn("<|user|> What is the role of the ATGS 3000", result)
        self.assertIn("<|user|> How do I use astrology", result)
    
    def test_empty_input_handling(self):
        """Test handling of empty input."""
        with self.assertRaises(ValueError):
            self.formatter.process_text("")
    
    def test_single_segment(self):
        """Test processing of single text segment."""
        single_text = "What is artificial intelligence?"
        result = self.formatter.process_text(single_text)
        
        self.assertIn("<|user|>", result)
        self.assertIn("artificial intelligence", result)


class TestFileProcessing(unittest.TestCase):
    """Test file processing capabilities."""
    
    def setUp(self):
        self.formatter = ConversationFormatter()
    
    def test_sample_file_processing(self):
        """Test processing of sample files."""
        # Test with the sample input file
        sample_file = Path("examples/sample_input.txt")
        if sample_file.exists():
            with open(sample_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            result = self.formatter.process_text(content)
            
            # Verify formatting
            self.assertIn("<|user|>", result)
            self.assertIn("<|assistant|>", result)
            
            # Count conversation turns
            user_count = result.count("<|user|>")
            assistant_count = result.count("<|assistant|>")
            
            # Should have multiple turns
            self.assertGreater(user_count, 0)
            self.assertGreater(assistant_count, 0)


def run_integration_test():
    """Run a complete integration test."""
    print("Running integration test...")
    
    formatter = ConversationFormatter()
    
    # Test data
    test_input = """What is machine learning? Machine learning is a subset of artificial intelligence that enables computers to learn from data. It uses algorithms to identify patterns and make predictions without being explicitly programmed for each task.

How does deep learning differ from traditional machine learning? Deep learning uses neural networks with multiple layers to automatically extract features from raw data. Traditional machine learning often requires manual feature engineering, while deep learning can learn complex representations automatically."""
    
    try:
        result = formatter.process_text(test_input)
        print("✓ Integration test passed")
        print("\nFormatted output:")
        print("-" * 50)
        print(result)
        print("-" * 50)
        return True
    except Exception as e:
        print(f"✗ Integration test failed: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("Running Text Formatter Tests")
    print("=" * 40)
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "=" * 40)
    
    # Run integration test
    run_integration_test()


if __name__ == "__main__":
    main()
