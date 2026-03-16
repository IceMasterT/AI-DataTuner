#!/usr/bin/env python3
"""
Batch processor for handling multiple files and advanced operations.
"""

import os
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from text_formatter import ConversationFormatter
from utils import validate_input
from config import SUPPORTED_EXTENSIONS


class BatchProcessor:
    """Process multiple files in batch mode."""
    
    def __init__(self):
        self.formatter = ConversationFormatter()
        self.results = []
    
    def process_directory(self, directory_path: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Process all text files in a directory.
        
        Args:
            directory_path: Path to directory
            recursive: Whether to process subdirectories
            
        Returns:
            List of processing results
        """
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Directory not found: {directory_path}")
        
        # Find text files
        pattern = "**/*" if recursive else "*"
        text_files = []
        
        for ext in SUPPORTED_EXTENSIONS:
            text_files.extend(directory.glob(f"{pattern}{ext}"))
        
        if not text_files:
            print(f"No text files found in {directory_path}")
            return []
        
        print(f"Found {len(text_files)} text files to process...")
        
        results = []
        for file_path in text_files:
            try:
                result = self.process_file(str(file_path))
                results.append(result)
                print(f"✓ Processed: {file_path.name}")
            except Exception as e:
                error_result = {
                    'input_file': str(file_path),
                    'success': False,
                    'error': str(e)
                }
                results.append(error_result)
                print(f"✗ Failed: {file_path.name} - {str(e)}")
        
        return results
    
    def process_file(self, file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Process a single file.
        
        Args:
            file_path: Input file path
            output_path: Output file path (optional)
            
        Returns:
            Processing result dictionary
        """
        input_path = Path(file_path)
        if not input_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read input file
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
        except Exception as e:
            raise Exception(f"Failed to read file: {str(e)}")
        
        # Validate input
        is_valid, error_msg = validate_input(raw_text)
        if not is_valid:
            raise ValueError(f"Invalid input text: {error_msg}")
        
        # Process text
        try:
            formatted_text = self.formatter.process_text(raw_text)
        except Exception as e:
            raise Exception(f"Failed to process text: {str(e)}")
        
        # Determine output path
        if not output_path:
            output_path = input_path.with_suffix('.formatted.txt')
        
        # Write output file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
        except Exception as e:
            raise Exception(f"Failed to write output file: {str(e)}")
        
        return {
            'input_file': str(input_path),
            'output_file': str(output_path),
            'success': True,
            'input_length': len(raw_text),
            'output_length': len(formatted_text),
            'segments_processed': len(formatted_text.split('\n\n'))
        }
    
    def process_multiple_files(self, file_paths: List[str], output_dir: str = None) -> List[Dict[str, Any]]:
        """
        Process multiple specific files.
        
        Args:
            file_paths: List of input file paths
            output_dir: Output directory (optional)
            
        Returns:
            List of processing results
        """
        if output_dir:
            output_directory = Path(output_dir)
            output_directory.mkdir(parents=True, exist_ok=True)
        
        results = []
        for file_path in file_paths:
            try:
                if output_dir:
                    input_name = Path(file_path).stem
                    output_path = output_directory / f"{input_name}.formatted.txt"
                else:
                    output_path = None
                
                result = self.process_file(file_path, str(output_path) if output_path else None)
                results.append(result)
                print(f"✓ Processed: {Path(file_path).name}")
                
            except Exception as e:
                error_result = {
                    'input_file': file_path,
                    'success': False,
                    'error': str(e)
                }
                results.append(error_result)
                print(f"✗ Failed: {Path(file_path).name} - {str(e)}")
        
        return results
    
    def generate_report(self, results: List[Dict[str, Any]], report_path: str = None):
        """
        Generate a processing report.
        
        Args:
            results: List of processing results
            report_path: Path to save report (optional)
        """
        successful = [r for r in results if r.get('success', False)]
        failed = [r for r in results if not r.get('success', False)]
        
        report = {
            'summary': {
                'total_files': len(results),
                'successful': len(successful),
                'failed': len(failed),
                'success_rate': len(successful) / len(results) * 100 if results else 0
            },
            'successful_files': successful,
            'failed_files': failed
        }
        
        if report_path:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to: {report_path}")
        
        # Print summary
        print("\n" + "="*50)
        print("PROCESSING SUMMARY")
        print("="*50)
        print(f"Total files: {report['summary']['total_files']}")
        print(f"Successful: {report['summary']['successful']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Success rate: {report['summary']['success_rate']:.1f}%")
        
        if failed:
            print("\nFailed files:")
            for fail in failed:
                print(f"  - {fail['input_file']}: {fail['error']}")


def main():
    """Main function for batch processing."""
    parser = argparse.ArgumentParser(description="Batch Text Formatter")
    parser.add_argument("input", help="Input file or directory path")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("-r", "--recursive", action="store_true", 
                       help="Process directories recursively")
    parser.add_argument("--report", help="Generate processing report")
    parser.add_argument("--files", nargs="+", help="Process specific files")
    
    args = parser.parse_args()
    
    processor = BatchProcessor()
    
    try:
        if args.files:
            # Process specific files
            results = processor.process_multiple_files(args.files, args.output)
        elif Path(args.input).is_dir():
            # Process directory
            results = processor.process_directory(args.input, args.recursive)
        else:
            # Process single file
            results = [processor.process_file(args.input, args.output)]
        
        # Generate report
        processor.generate_report(results, args.report)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
