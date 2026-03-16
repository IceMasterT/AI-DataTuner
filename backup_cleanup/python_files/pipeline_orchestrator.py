#!/usr/bin/env python3
"""
Pipeline Orchestrator for automated file processing workflow.
Manages input → filtered → output pipeline with multi-format support.
"""

import os
import shutil
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from ai_enhanced_processor import AIEnhancedTextProcessor, ProcessingConfig
from secure_text_processor import SecureTextProcessor


@dataclass
class PipelineConfig:
    """Configuration for the processing pipeline."""
    # Folder paths
    input_folder: str = "input"
    filtered_folder: str = "filtered"
    output_folder: str = "output"
    error_folder: str = "errors"
    archive_folder: str = "archive"
    
    # Processing settings
    enable_ai_processing: bool = True
    enable_security_filtering: bool = True
    auto_move_files: bool = True
    parallel_processing: bool = True
    max_workers: int = 4
    
    # File monitoring
    watch_input_folder: bool = True
    processing_interval: float = 5.0  # seconds
    
    # Output settings
    output_format: str = "qwen"
    preserve_original_structure: bool = True
    
    # AI settings (loaded from .env)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    daily_cost_limit: float = 20.0
    enable_content_enhancement: bool = True


class FileProcessor:
    """Base class for file processors."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def can_process(self, file_path: Path) -> bool:
        """Check if this processor can handle the file."""
        # Default implementation checks file extension
        supported_extensions = getattr(self, 'supported_extensions', [])
        return file_path.suffix.lower() in supported_extensions

    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process the file and return results."""
        result = {
            'success': False,
            'file_path': str(file_path),
            'segments': [],
            'metadata': {},
            'errors': []
        }

        try:
            if not self.can_process(file_path):
                result['errors'].append(f"Cannot process file type: {file_path.suffix}")
                return result

            # Extract text segments
            segments = self.extract_text_segments(file_path)

            if segments:
                result['success'] = True
                result['segments'] = segments
                result['metadata'] = {
                    'file_size': file_path.stat().st_size,
                    'segment_count': len(segments),
                    'processed_at': datetime.now().isoformat()
                }
                self.logger.info(f"Successfully processed {file_path}: {len(segments)} segments")
            else:
                result['errors'].append("No text segments extracted from file")

        except Exception as e:
            result['errors'].append(f"Processing error: {str(e)}")
            self.logger.error(f"Error processing {file_path}: {e}")

        return result

    def extract_text_segments(self, file_path: Path) -> List[str]:
        """Extract text segments from the file."""
        # Default implementation for text files
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Split into paragraphs as basic segmentation
            segments = [seg.strip() for seg in content.split('\n\n') if seg.strip()]
            return segments

        except Exception as e:
            self.logger.error(f"Error extracting text from {file_path}: {e}")
            return []


class TextFileProcessor(FileProcessor):
    """Processor for plain text files."""

    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self.supported_extensions = ['.txt', '.md', '.rst']

    def extract_text_segments(self, file_path: Path) -> List[str]:
        """Extract text segments from text files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Clean and normalize text
            content = content.strip()

            # Split by double newlines (paragraphs)
            segments = [seg.strip() for seg in content.split('\n\n') if seg.strip()]

            # If no paragraph breaks, split by single newlines
            if len(segments) <= 1 and '\n' in content:
                segments = [seg.strip() for seg in content.split('\n') if seg.strip()]

            # Filter out very short segments
            segments = [seg for seg in segments if len(seg) > 20]

            return segments

        except Exception as e:
            self.logger.error(f"Error processing text file {file_path}: {e}")
            return []


class JSONFileProcessor(FileProcessor):
    """Processor for JSON files."""

    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self.supported_extensions = ['.json', '.jsonl']

    def extract_text_segments(self, file_path: Path) -> List[str]:
        """Extract text segments from JSON files."""
        segments = []

        try:
            if file_path.suffix.lower() == '.jsonl':
                # Process JSONL (JSON Lines)
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                text_content = self._extract_text_from_json(data)
                                if text_content:
                                    segments.extend(text_content)
                            except json.JSONDecodeError as e:
                                self.logger.warning(f"Invalid JSON on line {line_num} in {file_path}: {e}")
            else:
                # Process regular JSON
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    text_content = self._extract_text_from_json(data)
                    if text_content:
                        segments.extend(text_content)

        except Exception as e:
            self.logger.error(f"Error processing JSON file {file_path}: {e}")

        return segments

    def _extract_text_from_json(self, data) -> List[str]:
        """Extract text content from JSON data structure."""
        text_segments = []

        if isinstance(data, dict):
            # Look for common text fields
            text_fields = ['text', 'content', 'message', 'description', 'body', 'prompt', 'response', 'answer', 'question']

            for field in text_fields:
                if field in data and isinstance(data[field], str) and len(data[field].strip()) > 20:
                    text_segments.append(data[field].strip())

            # Recursively process nested objects
            for value in data.values():
                if isinstance(value, (dict, list)):
                    text_segments.extend(self._extract_text_from_json(value))

        elif isinstance(data, list):
            for item in data:
                text_segments.extend(self._extract_text_from_json(item))

        return text_segments


class CSVFileProcessor(FileProcessor):
    """Processor for CSV files."""

    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self.supported_extensions = ['.csv']

    def extract_text_segments(self, file_path: Path) -> List[str]:
        """Extract text segments from CSV files."""
        segments = []

        try:
            import csv

            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                # Try to detect delimiter
                sample = f.read(1024)
                f.seek(0)

                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter

                reader = csv.DictReader(f, delimiter=delimiter)

                for row_num, row in enumerate(reader, 1):
                    # Look for text content in each row
                    for column, value in row.items():
                        if value and isinstance(value, str) and len(value.strip()) > 20:
                            segments.append(value.strip())

        except Exception as e:
            self.logger.error(f"Error processing CSV file {file_path}: {e}")

        return segments


class PipelineOrchestrator:
    """Main orchestrator for the processing pipeline."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = self._setup_logging()
        
        # Create folder structure
        self._create_folders()
        
        # Initialize processors
        self.file_processors = []
        self.ai_processor = None
        self.security_processor = None
        
        self._init_processors()
        
        # Processing statistics
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'total_cost': 0.0,
            'processing_time': 0.0,
            'start_time': datetime.now()
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the pipeline."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # File handler
        log_file = logs_dir / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _create_folders(self):
        """Create the pipeline folder structure."""
        folders = [
            self.config.input_folder,
            self.config.filtered_folder,
            self.config.output_folder,
            self.config.error_folder,
            self.config.archive_folder
        ]
        
        for folder in folders:
            Path(folder).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created/verified folder: {folder}")
    
    def _init_processors(self):
        """Initialize file processors and AI components."""
        # Import and register file processors
        try:
            from file_processors import (
                PDFProcessor, CSVProcessor, JSONProcessor, 
                JSONLProcessor, TextProcessor
            )
            
            self.file_processors = [
                PDFProcessor(self.config),
                CSVProcessor(self.config),
                JSONProcessor(self.config),
                JSONLProcessor(self.config),
                TextProcessor(self.config)
            ]
            
            self.logger.info(f"Registered {len(self.file_processors)} file processors")
        
        except ImportError as e:
            self.logger.warning(f"Could not import file processors: {e}")
            self.file_processors = []
        
        # Initialize AI processor
        if self.config.enable_ai_processing and self.config.openai_api_key:
            try:
                ai_config = ProcessingConfig(
                    openai_api_key=self.config.openai_api_key,
                    openai_model=self.config.openai_model,
                    daily_cost_limit=self.config.daily_cost_limit,
                    enable_ai_classification=True,
                    enable_content_enhancement=self.config.enable_content_enhancement,
                    enable_security_filtering=False  # Handled separately
                )
                
                self.ai_processor = AIEnhancedTextProcessor(ai_config, self.config.output_format)
                self.logger.info("AI processor initialized")
            
            except Exception as e:
                self.logger.error(f"Failed to initialize AI processor: {e}")
                self.ai_processor = None
        
        # Initialize security processor
        if self.config.enable_security_filtering:
            try:
                self.security_processor = SecureTextProcessor(
                    output_format=self.config.output_format,
                    aggressive_mode=False
                )
                self.logger.info("Security processor initialized")
            
            except Exception as e:
                self.logger.error(f"Failed to initialize security processor: {e}")
                self.security_processor = None
    
    def get_file_processor(self, file_path: Path) -> Optional[FileProcessor]:
        """Get the appropriate processor for a file."""
        for processor in self.file_processors:
            if processor.can_process(file_path):
                return processor
        return None
    
    def process_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single file through the pipeline."""
        start_time = time.time()
        result = {
            'file_path': str(file_path),
            'success': False,
            'stage': 'initialization',
            'error': None,
            'output_files': [],
            'processing_time': 0.0,
            'cost': 0.0,
            'segments_processed': 0
        }
        
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            # Stage 1: File format processing and text extraction
            result['stage'] = 'text_extraction'
            processor = self.get_file_processor(file_path)
            
            if not processor:
                raise ValueError(f"No processor available for file type: {file_path.suffix}")
            
            # Extract text segments
            text_segments = processor.extract_text_segments(file_path)
            result['segments_processed'] = len(text_segments)
            
            if not text_segments:
                raise ValueError("No text content extracted from file")
            
            self.logger.info(f"Extracted {len(text_segments)} text segments")
            
            # Stage 2: Security filtering
            if self.security_processor:
                result['stage'] = 'security_filtering'
                filtered_segments = []
                
                for segment in text_segments:
                    security_result = self.security_processor.process_text(segment)
                    
                    if security_result['success']:
                        filtered_segments.append(security_result.get('processed_text', segment))
                    else:
                        self.logger.warning(f"Security filter blocked segment: {segment[:50]}...")
                
                text_segments = filtered_segments
                self.logger.info(f"Security filtering completed: {len(text_segments)} segments passed")
            
            # Stage 3: AI processing and enhancement
            if self.ai_processor and text_segments:
                result['stage'] = 'ai_processing'
                enhanced_segments = []
                total_cost = 0.0
                
                for segment in text_segments:
                    ai_result = self.ai_processor.process_text(segment, str(file_path))
                    
                    if ai_result.success:
                        enhanced_segments.append(ai_result.processed_text)
                        total_cost += ai_result.total_cost
                    else:
                        # Fallback to original segment
                        enhanced_segments.append(segment)
                        self.logger.warning(f"AI processing failed for segment, using original")
                
                text_segments = enhanced_segments
                result['cost'] = total_cost
                self.logger.info(f"AI processing completed: cost ${total_cost:.4f}")
            
            # Stage 4: Output generation
            result['stage'] = 'output_generation'
            output_files = self._generate_output_files(file_path, text_segments)
            result['output_files'] = output_files
            
            # Stage 5: File movement
            if self.config.auto_move_files:
                result['stage'] = 'file_movement'
                self._move_processed_file(file_path)
            
            result['success'] = True
            result['processing_time'] = time.time() - start_time
            
            self.logger.info(f"Successfully processed {file_path} in {result['processing_time']:.2f}s")
            
        except Exception as e:
            result['error'] = str(e)
            result['processing_time'] = time.time() - start_time
            
            self.logger.error(f"Failed to process {file_path} at stage {result['stage']}: {e}")
            
            # Move to error folder
            if self.config.auto_move_files:
                self._move_error_file(file_path, str(e))
        
        return result
    
    def _generate_output_files(self, input_file: Path, text_segments: List[str]) -> List[str]:
        """Generate output files from processed text segments."""
        output_files = []
        
        # Create output filename
        base_name = input_file.stem
        output_file = Path(self.config.output_folder) / f"{base_name}_processed.txt"
        
        # Combine segments into conversation format
        if text_segments:
            # Simple combination - could be enhanced with better formatting
            combined_text = "\n\n".join(text_segments)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(combined_text)
            
            output_files.append(str(output_file))
            
            # Also create metadata file
            metadata_file = Path(self.config.output_folder) / f"{base_name}_metadata.json"
            metadata = {
                'original_file': str(input_file),
                'processed_at': datetime.now().isoformat(),
                'segments_count': len(text_segments),
                'output_format': self.config.output_format,
                'ai_processing': self.config.enable_ai_processing,
                'security_filtering': self.config.enable_security_filtering
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            output_files.append(str(metadata_file))
        
        return output_files
    
    def _move_processed_file(self, file_path: Path):
        """Move successfully processed file to archive."""
        archive_path = Path(self.config.archive_folder) / file_path.name
        
        # Ensure unique filename
        counter = 1
        while archive_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            archive_path = Path(self.config.archive_folder) / f"{stem}_{counter}{suffix}"
            counter += 1
        
        shutil.move(str(file_path), str(archive_path))
        self.logger.info(f"Moved processed file to archive: {archive_path}")
    
    def _move_error_file(self, file_path: Path, error_message: str):
        """Move failed file to error folder with error log."""
        error_path = Path(self.config.error_folder) / file_path.name
        
        # Ensure unique filename
        counter = 1
        while error_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            error_path = Path(self.config.error_folder) / f"{stem}_{counter}{suffix}"
            counter += 1
        
        shutil.move(str(file_path), str(error_path))
        
        # Create error log
        error_log_path = error_path.with_suffix('.error.txt')
        with open(error_log_path, 'w', encoding='utf-8') as f:
            f.write(f"Error processing file: {file_path}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Error: {error_message}\n")
        
        self.logger.info(f"Moved error file: {error_path}")
    
    def process_input_folder(self) -> Dict[str, Any]:
        """Process all files in the input folder."""
        input_path = Path(self.config.input_folder)
        
        # Find all processable files
        files_to_process = []
        supported_extensions = {'.pdf', '.csv', '.json', '.jsonl', '.txt', '.md'}
        
        for file_path in input_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                files_to_process.append(file_path)
        
        if not files_to_process:
            self.logger.info("No files to process in input folder")
            return {'files_processed': 0, 'files_failed': 0, 'total_cost': 0.0}
        
        self.logger.info(f"Found {len(files_to_process)} files to process")
        
        # Process files
        results = []
        
        if self.config.parallel_processing and len(files_to_process) > 1:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                future_to_file = {
                    executor.submit(self.process_single_file, file_path): file_path
                    for file_path in files_to_process
                }
                
                for future in as_completed(future_to_file):
                    result = future.result()
                    results.append(result)
        else:
            # Sequential processing
            for file_path in files_to_process:
                result = self.process_single_file(file_path)
                results.append(result)
        
        # Update statistics
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        total_cost = sum(r['cost'] for r in results)
        
        self.stats['files_processed'] += successful
        self.stats['files_failed'] += failed
        self.stats['total_cost'] += total_cost
        
        summary = {
            'files_processed': successful,
            'files_failed': failed,
            'total_cost': total_cost,
            'results': results
        }
        
        self.logger.info(f"Batch processing complete: {successful} successful, {failed} failed, cost: ${total_cost:.4f}")
        
        return summary
    
    def start_monitoring(self):
        """Start monitoring the input folder for new files."""
        self.logger.info("Starting input folder monitoring...")
        
        try:
            while True:
                # Process any files in input folder
                summary = self.process_input_folder()
                
                if summary['files_processed'] > 0 or summary['files_failed'] > 0:
                    self.logger.info(f"Processed {summary['files_processed']} files, {summary['files_failed']} failed")
                
                # Wait before next check
                time.sleep(self.config.processing_interval)
        
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and statistics."""
        input_files = len(list(Path(self.config.input_folder).glob('*')))
        filtered_files = len(list(Path(self.config.filtered_folder).glob('*')))
        output_files = len(list(Path(self.config.output_folder).glob('*')))
        error_files = len(list(Path(self.config.error_folder).glob('*')))
        
        runtime = datetime.now() - self.stats['start_time']
        
        return {
            'pipeline_status': {
                'input_files_pending': input_files,
                'filtered_files': filtered_files,
                'output_files': output_files,
                'error_files': error_files
            },
            'processing_stats': self.stats,
            'runtime': str(runtime),
            'configuration': {
                'ai_processing': self.config.enable_ai_processing,
                'security_filtering': self.config.enable_security_filtering,
                'parallel_processing': self.config.parallel_processing,
                'output_format': self.config.output_format
            }
        }
