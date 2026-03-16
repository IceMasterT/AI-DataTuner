#!/usr/bin/env python3
"""
Advanced data preparation features for extracting Q&A pairs from various sources.
Supports CSV, JSON, structured text, and other formats.
"""

import csv
import json
import re
import argparse
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
from text_formatter import ConversationFormatter
from chunking_strategies import ChunkingFactory, ChunkingStrategy
from format_templates import FormatFactory, ConversationFormat


class DataExtractor:
    """Extract Q&A pairs from various data sources."""
    
    def extract_from_csv(self, file_path: str, question_col: str = None, 
                        answer_col: str = None) -> List[Tuple[str, str]]:
        """
        Extract Q&A pairs from CSV file.
        
        Args:
            file_path: Path to CSV file
            question_col: Column name for questions (auto-detect if None)
            answer_col: Column name for answers (auto-detect if None)
            
        Returns:
            List of (question, answer) tuples
        """
        pairs = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
            # Auto-detect columns if not specified
            if not question_col:
                question_col = self._find_question_column(headers)
            if not answer_col:
                answer_col = self._find_answer_column(headers)
            
            if not question_col or not answer_col:
                raise ValueError("Could not identify question and answer columns")
            
            for row in reader:
                question = row.get(question_col, '').strip()
                answer = row.get(answer_col, '').strip()
                
                if question and answer:
                    pairs.append((question, answer))
        
        return pairs
    
    def extract_from_json(self, file_path: str, question_key: str = None,
                         answer_key: str = None) -> List[Tuple[str, str]]:
        """
        Extract Q&A pairs from JSON file.
        
        Args:
            file_path: Path to JSON file
            question_key: Key for questions (auto-detect if None)
            answer_key: Key for answers (auto-detect if None)
            
        Returns:
            List of (question, answer) tuples
        """
        pairs = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            # Array of objects
            for item in data:
                if isinstance(item, dict):
                    # Auto-detect keys if not specified
                    if not question_key:
                        question_key = self._find_question_key(item.keys())
                    if not answer_key:
                        answer_key = self._find_answer_key(item.keys())
                    
                    question = item.get(question_key, '').strip()
                    answer = item.get(answer_key, '').strip()
                    
                    if question and answer:
                        pairs.append((question, answer))
        
        elif isinstance(data, dict):
            # Single object or nested structure
            pairs.extend(self._extract_from_dict(data, question_key, answer_key))
        
        return pairs
    
    def extract_from_structured_text(self, file_path: str, 
                                   chunking_strategy: str = "heading") -> List[Tuple[str, str]]:
        """
        Extract Q&A pairs from structured text using chunking strategies.
        
        Args:
            file_path: Path to text file
            chunking_strategy: Strategy to use for chunking
            
        Returns:
            List of (question, answer) tuples
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Create chunker
        try:
            strategy_enum = ChunkingStrategy(chunking_strategy.lower())
            chunker = ChunkingFactory.create_chunker(strategy_enum)
        except ValueError:
            raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")
        
        # Extract chunks
        return chunker.chunk_content(text)
    
    def extract_from_faq(self, file_path: str) -> List[Tuple[str, str]]:
        """
        Extract Q&A pairs from FAQ-style text.
        
        Args:
            file_path: Path to FAQ file
            
        Returns:
            List of (question, answer) tuples
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        pairs = []
        
        # Common FAQ patterns
        patterns = [
            r'Q:\s*(.+?)\s*A:\s*(.+?)(?=Q:|$)',  # Q: ... A: ...
            r'Question:\s*(.+?)\s*Answer:\s*(.+?)(?=Question:|$)',  # Question: ... Answer: ...
            r'(\d+\.\s*.+?\?)\s*(.+?)(?=\d+\.|$)',  # 1. Question? Answer
            r'(.+?\?)\s*(.+?)(?=.+?\?|$)',  # Question? Answer
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            for question, answer in matches:
                question = question.strip()
                answer = answer.strip()
                
                # Clean up
                question = re.sub(r'^\d+\.\s*', '', question)  # Remove numbering
                
                if question and answer and len(question) > 10 and len(answer) > 10:
                    pairs.append((question, answer))
        
        return pairs
    
    def _find_question_column(self, headers: List[str]) -> Optional[str]:
        """Find the column that likely contains questions."""
        question_indicators = ['question', 'q', 'query', 'prompt', 'input', 'instruction']
        
        for header in headers:
            if any(indicator in header.lower() for indicator in question_indicators):
                return header
        
        return headers[0] if headers else None  # Fallback to first column
    
    def _find_answer_column(self, headers: List[str]) -> Optional[str]:
        """Find the column that likely contains answers."""
        answer_indicators = ['answer', 'a', 'response', 'output', 'reply', 'solution']
        
        for header in headers:
            if any(indicator in header.lower() for indicator in answer_indicators):
                return header
        
        return headers[1] if len(headers) > 1 else None  # Fallback to second column
    
    def _find_question_key(self, keys: List[str]) -> Optional[str]:
        """Find the key that likely contains questions."""
        question_indicators = ['question', 'q', 'query', 'prompt', 'input', 'instruction']
        
        for key in keys:
            if any(indicator in key.lower() for indicator in question_indicators):
                return key
        
        return list(keys)[0] if keys else None
    
    def _find_answer_key(self, keys: List[str]) -> Optional[str]:
        """Find the key that likely contains answers."""
        answer_indicators = ['answer', 'a', 'response', 'output', 'reply', 'solution']
        
        for key in keys:
            if any(indicator in key.lower() for indicator in answer_indicators):
                return key
        
        return list(keys)[1] if len(keys) > 1 else None
    
    def _extract_from_dict(self, data: Dict[str, Any], question_key: str = None,
                          answer_key: str = None) -> List[Tuple[str, str]]:
        """Extract Q&A pairs from dictionary structure."""
        pairs = []
        
        # If it's a direct Q&A mapping
        if question_key and answer_key:
            question = data.get(question_key, '').strip()
            answer = data.get(answer_key, '').strip()
            if question and answer:
                pairs.append((question, answer))
        else:
            # Try to find Q&A patterns in the structure
            for key, value in data.items():
                if isinstance(value, str) and '?' in value:
                    # Potential question
                    question = value.strip()
                    # Look for corresponding answer
                    for other_key, other_value in data.items():
                        if (other_key != key and isinstance(other_value, str) and 
                            len(other_value) > len(question)):
                            pairs.append((question, other_value.strip()))
                            break
        
        return pairs


class DataPreparationPipeline:
    """Complete pipeline for data preparation and conversion."""
    
    def __init__(self, output_format: str = "qwen", **format_kwargs):
        self.extractor = DataExtractor()
        self.formatter = ConversationFormatter(output_format, **format_kwargs)
        self.output_format = output_format
        self.format_kwargs = format_kwargs
    
    def process_file(self, file_path: str, file_type: str = None, 
                    output_path: str = None, **extraction_kwargs) -> Dict[str, Any]:
        """
        Process a single file through the complete pipeline.
        
        Args:
            file_path: Input file path
            file_type: Type of file (csv, json, text, faq) - auto-detect if None
            output_path: Output file path
            **extraction_kwargs: Additional arguments for extraction
            
        Returns:
            Processing result dictionary
        """
        file_path = Path(file_path)
        
        # Auto-detect file type if not specified
        if not file_type:
            file_type = self._detect_file_type(file_path)
        
        # Extract Q&A pairs
        try:
            if file_type == 'csv':
                pairs = self.extractor.extract_from_csv(str(file_path), **extraction_kwargs)
            elif file_type == 'json':
                pairs = self.extractor.extract_from_json(str(file_path), **extraction_kwargs)
            elif file_type == 'faq':
                pairs = self.extractor.extract_from_faq(str(file_path))
            elif file_type == 'text':
                pairs = self.extractor.extract_from_structured_text(str(file_path), **extraction_kwargs)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        
        except Exception as e:
            return {
                'input_file': str(file_path),
                'success': False,
                'error': f"Extraction failed: {str(e)}"
            }
        
        if not pairs:
            return {
                'input_file': str(file_path),
                'success': False,
                'error': "No Q&A pairs extracted"
            }
        
        # Format the pairs
        try:
            template = FormatFactory.create_template(
                ConversationFormat(self.output_format), **self.format_kwargs
            )
            formatted_text = template.format_conversation(pairs)
        except Exception as e:
            return {
                'input_file': str(file_path),
                'success': False,
                'error': f"Formatting failed: {str(e)}"
            }
        
        # Save output
        if not output_path:
            output_path = file_path.with_suffix(f'.{self.output_format}.txt')
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
        except Exception as e:
            return {
                'input_file': str(file_path),
                'success': False,
                'error': f"Save failed: {str(e)}"
            }
        
        return {
            'input_file': str(file_path),
            'output_file': str(output_path),
            'success': True,
            'pairs_extracted': len(pairs),
            'output_format': self.output_format
        }
    
    def batch_process(self, input_files: List[str], output_dir: str = None,
                     **kwargs) -> List[Dict[str, Any]]:
        """
        Process multiple files in batch.
        
        Args:
            input_files: List of input file paths
            output_dir: Output directory
            **kwargs: Additional arguments for processing
            
        Returns:
            List of processing results
        """
        results = []
        
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        for input_file in input_files:
            input_path = Path(input_file)
            
            if output_dir:
                output_path = output_dir / f"{input_path.stem}.{self.output_format}.txt"
            else:
                output_path = None
            
            result = self.process_file(input_file, output_path=output_path, **kwargs)
            results.append(result)
        
        return results
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Auto-detect file type based on extension and content."""
        extension = file_path.suffix.lower()
        
        if extension == '.csv':
            return 'csv'
        elif extension == '.json':
            return 'json'
        elif 'faq' in file_path.name.lower():
            return 'faq'
        else:
            return 'text'


def main():
    """Main function for data preparation CLI."""
    parser = argparse.ArgumentParser(description="Advanced Data Preparation for Q&A Extraction")
    parser.add_argument("input", help="Input file or directory")
    parser.add_argument("-t", "--type", choices=['csv', 'json', 'text', 'faq'],
                       help="Input file type (auto-detect if not specified)")
    parser.add_argument("-f", "--format", default="qwen",
                       choices=FormatFactory.get_available_formats(),
                       help="Output format")
    parser.add_argument("-o", "--output", help="Output file or directory")
    parser.add_argument("--chunking", default="heading",
                       choices=ChunkingFactory.get_available_strategies(),
                       help="Chunking strategy for text files")
    parser.add_argument("--question-col", help="Question column name for CSV")
    parser.add_argument("--answer-col", help="Answer column name for CSV")
    parser.add_argument("--question-key", help="Question key for JSON")
    parser.add_argument("--answer-key", help="Answer key for JSON")
    parser.add_argument("--system-message", help="System message for OpenAI format")
    
    args = parser.parse_args()
    
    # Prepare format kwargs
    format_kwargs = {}
    if args.system_message and args.format == "openai":
        format_kwargs["system_message"] = args.system_message
    
    # Prepare extraction kwargs
    extraction_kwargs = {}
    if args.question_col:
        extraction_kwargs["question_col"] = args.question_col
    if args.answer_col:
        extraction_kwargs["answer_col"] = args.answer_col
    if args.question_key:
        extraction_kwargs["question_key"] = args.question_key
    if args.answer_key:
        extraction_kwargs["answer_key"] = args.answer_key
    if args.chunking:
        extraction_kwargs["chunking_strategy"] = args.chunking
    
    # Create pipeline
    pipeline = DataPreparationPipeline(args.format, **format_kwargs)
    
    try:
        input_path = Path(args.input)
        
        if input_path.is_file():
            # Single file
            result = pipeline.process_file(
                str(input_path), args.type, args.output, **extraction_kwargs
            )
            
            if result['success']:
                print(f"✓ Processed: {result['input_file']}")
                print(f"  Extracted: {result['pairs_extracted']} Q&A pairs")
                print(f"  Output: {result['output_file']}")
            else:
                print(f"✗ Failed: {result['input_file']} - {result['error']}")
        
        elif input_path.is_dir():
            # Directory
            input_files = list(input_path.glob("*"))
            input_files = [str(f) for f in input_files if f.is_file()]
            
            results = pipeline.batch_process(input_files, args.output, **extraction_kwargs)
            
            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]
            
            print(f"Processed {len(successful)}/{len(results)} files successfully")
            
            total_pairs = sum(r.get('pairs_extracted', 0) for r in successful)
            print(f"Total Q&A pairs extracted: {total_pairs}")
            
            if failed:
                print("\nFailed files:")
                for fail in failed:
                    print(f"  {fail['input_file']}: {fail['error']}")
        
        else:
            print(f"Error: Input path not found: {args.input}")
            return 1
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
