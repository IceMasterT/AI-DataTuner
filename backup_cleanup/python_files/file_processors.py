#!/usr/bin/env python3
"""
Multi-format file processors for the pipeline.
Supports PDF, CSV, JSONL, JSON, and text file processing with data extraction.
"""

import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

from pipeline_orchestrator import FileProcessor, PipelineConfig


class PDFProcessor(FileProcessor):
    """Processor for PDF files."""
    
    def can_process(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.pdf'
    
    def extract_text_segments(self, file_path: Path) -> List[str]:
        """Extract text segments from PDF."""
        try:
            # Try to import PDF processing library
            try:
                import PyPDF2
                return self._extract_with_pypdf2(file_path)
            except ImportError:
                try:
                    import pdfplumber
                    return self._extract_with_pdfplumber(file_path)
                except ImportError:
                    self.logger.warning("No PDF library available. Install PyPDF2 or pdfplumber.")
                    return []
        
        except Exception as e:
            self.logger.error(f"Error processing PDF {file_path}: {e}")
            return []
    
    def _extract_with_pypdf2(self, file_path: Path) -> List[str]:
        """Extract text using PyPDF2."""
        import PyPDF2
        
        segments = []
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        # Split into paragraphs
                        paragraphs = self._split_into_paragraphs(text)
                        segments.extend(paragraphs)
                
                except Exception as e:
                    self.logger.warning(f"Error extracting page {page_num}: {e}")
        
        return segments
    
    def _extract_with_pdfplumber(self, file_path: Path) -> List[str]:
        """Extract text using pdfplumber."""
        import pdfplumber
        
        segments = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        # Split into paragraphs
                        paragraphs = self._split_into_paragraphs(text)
                        segments.extend(paragraphs)
                
                except Exception as e:
                    self.logger.warning(f"Error extracting page {page_num}: {e}")
        
        return segments
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into meaningful paragraphs."""
        # Clean up text
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'\n+', '\n', text)  # Normalize line breaks
        
        # Split by double line breaks or sentence patterns
        paragraphs = re.split(r'\n\s*\n|\. {2,}', text)
        
        # Filter and clean paragraphs
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if len(para) > 50:  # Minimum paragraph length
                cleaned_paragraphs.append(para)
        
        return cleaned_paragraphs


class CSVProcessor(FileProcessor):
    """Processor for CSV files."""
    
    def can_process(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.csv'
    
    def extract_text_segments(self, file_path: Path) -> List[str]:
        """Extract text segments from CSV."""
        try:
            segments = []
            
            with open(file_path, 'r', encoding='utf-8', newline='') as file:
                # Try to detect delimiter
                sample = file.read(1024)
                file.seek(0)
                
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(file, delimiter=delimiter)
                
                for row_num, row in enumerate(reader):
                    try:
                        # Convert row to conversation format
                        conversation_segments = self._row_to_conversation(row, row_num)
                        segments.extend(conversation_segments)
                    
                    except Exception as e:
                        self.logger.warning(f"Error processing CSV row {row_num}: {e}")
            
            return segments
        
        except Exception as e:
            self.logger.error(f"Error processing CSV {file_path}: {e}")
            return []
    
    def _row_to_conversation(self, row: Dict[str, str], row_num: int) -> List[str]:
        """Convert CSV row to conversation segments."""
        segments = []
        
        # Common column patterns for Q&A data
        question_columns = ['question', 'q', 'query', 'input', 'prompt', 'instruction']
        answer_columns = ['answer', 'a', 'response', 'output', 'completion', 'reply']
        
        # Find question and answer columns
        question_col = None
        answer_col = None
        
        for col in row.keys():
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in question_columns):
                question_col = col
            elif any(pattern in col_lower for pattern in answer_columns):
                answer_col = col
        
        # Extract Q&A pairs
        if question_col and answer_col:
            question = row.get(question_col, '').strip()
            answer = row.get(answer_col, '').strip()
            
            if question and answer:
                segments.append(f"<|user|> {question}")
                segments.append(f"<|assistant|> {answer}")
        
        else:
            # Fallback: combine all non-empty columns
            text_parts = []
            for col, value in row.items():
                if value and value.strip():
                    text_parts.append(f"{col}: {value.strip()}")
            
            if text_parts:
                combined_text = " | ".join(text_parts)
                segments.append(combined_text)
        
        return segments


class JSONProcessor(FileProcessor):
    """Processor for JSON files."""
    
    def can_process(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.json'
    
    def extract_text_segments(self, file_path: Path) -> List[str]:
        """Extract text segments from JSON."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            segments = []
            
            if isinstance(data, list):
                # Array of objects
                for item in data:
                    item_segments = self._extract_from_json_object(item)
                    segments.extend(item_segments)
            
            elif isinstance(data, dict):
                # Single object
                item_segments = self._extract_from_json_object(data)
                segments.extend(item_segments)
            
            return segments
        
        except Exception as e:
            self.logger.error(f"Error processing JSON {file_path}: {e}")
            return []
    
    def _extract_from_json_object(self, obj: Any) -> List[str]:
        """Extract text from a JSON object."""
        segments = []
        
        if isinstance(obj, dict):
            # Look for conversation patterns
            if self._is_conversation_format(obj):
                conv_segments = self._extract_conversation(obj)
                segments.extend(conv_segments)
            
            else:
                # Extract text from all string values
                text_values = self._extract_text_values(obj)
                segments.extend(text_values)
        
        elif isinstance(obj, str) and len(obj.strip()) > 20:
            segments.append(obj.strip())
        
        return segments
    
    def _is_conversation_format(self, obj: Dict) -> bool:
        """Check if object is in conversation format."""
        # ShareGPT format
        if 'conversations' in obj or 'messages' in obj:
            return True
        
        # Simple Q&A format
        question_keys = ['question', 'q', 'input', 'prompt', 'instruction']
        answer_keys = ['answer', 'a', 'output', 'response', 'completion']
        
        has_question = any(key in obj for key in question_keys)
        has_answer = any(key in obj for key in answer_keys)
        
        return has_question and has_answer
    
    def _extract_conversation(self, obj: Dict) -> List[str]:
        """Extract conversation from structured format."""
        segments = []
        
        # ShareGPT format
        if 'conversations' in obj:
            for msg in obj['conversations']:
                if isinstance(msg, dict) and 'from' in msg and 'value' in msg:
                    role = 'user' if msg['from'] in ['human', 'user'] else 'assistant'
                    segments.append(f"<|{role}|> {msg['value']}")
        
        elif 'messages' in obj:
            for msg in obj['messages']:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    role = msg['role']
                    if role in ['user', 'assistant']:
                        segments.append(f"<|{role}|> {msg['content']}")
        
        # Simple Q&A format
        else:
            question_keys = ['question', 'q', 'input', 'prompt', 'instruction']
            answer_keys = ['answer', 'a', 'output', 'response', 'completion']
            
            question = None
            answer = None
            
            for key in question_keys:
                if key in obj and obj[key]:
                    question = obj[key]
                    break
            
            for key in answer_keys:
                if key in obj and obj[key]:
                    answer = obj[key]
                    break
            
            if question and answer:
                segments.append(f"<|user|> {question}")
                segments.append(f"<|assistant|> {answer}")
        
        return segments
    
    def _extract_text_values(self, obj: Any, max_depth: int = 3) -> List[str]:
        """Recursively extract text values from object."""
        if max_depth <= 0:
            return []
        
        text_values = []
        
        if isinstance(obj, dict):
            for value in obj.values():
                text_values.extend(self._extract_text_values(value, max_depth - 1))
        
        elif isinstance(obj, list):
            for item in obj:
                text_values.extend(self._extract_text_values(item, max_depth - 1))
        
        elif isinstance(obj, str) and len(obj.strip()) > 20:
            text_values.append(obj.strip())
        
        return text_values


class JSONLProcessor(FileProcessor):
    """Processor for JSONL (JSON Lines) files."""
    
    def can_process(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.jsonl', '.ndjson']
    
    def extract_text_segments(self, file_path: Path) -> List[str]:
        """Extract text segments from JSONL."""
        try:
            segments = []
            json_processor = JSONProcessor(self.config)
            
            with open(file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        obj = json.loads(line)
                        line_segments = json_processor._extract_from_json_object(obj)
                        segments.extend(line_segments)
                    
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Invalid JSON on line {line_num}: {e}")
                    except Exception as e:
                        self.logger.warning(f"Error processing line {line_num}: {e}")
            
            return segments
        
        except Exception as e:
            self.logger.error(f"Error processing JSONL {file_path}: {e}")
            return []


class TextProcessor(FileProcessor):
    """Processor for plain text and markdown files."""
    
    def can_process(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.txt', '.md', '.markdown']
    
    def extract_text_segments(self, file_path: Path) -> List[str]:
        """Extract text segments from text files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Use existing text segmentation logic
            from utils import split_text_intelligently, preprocess_text
            
            # Preprocess and segment
            processed_content = preprocess_text(content)
            segments = split_text_intelligently(processed_content)
            
            # Filter out very short segments
            filtered_segments = [seg for seg in segments if len(seg.strip()) > 20]
            
            return filtered_segments
        
        except Exception as e:
            self.logger.error(f"Error processing text file {file_path}: {e}")
            return []


class AdvancedDataExtractor:
    """Advanced data extraction utilities for complex formats."""
    
    @staticmethod
    def extract_qa_pairs_from_text(text: str) -> List[Tuple[str, str]]:
        """Extract Q&A pairs from unstructured text."""
        qa_pairs = []
        
        # Pattern for Q: ... A: ... format
        qa_pattern = r'Q:\s*(.+?)\s*A:\s*(.+?)(?=Q:|$)'
        matches = re.findall(qa_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for question, answer in matches:
            question = question.strip()
            answer = answer.strip()
            if question and answer:
                qa_pairs.append((question, answer))
        
        # Pattern for numbered Q&A
        numbered_pattern = r'(\d+)\.\s*(.+?)\s*(?:Answer|A):\s*(.+?)(?=\d+\.|$)'
        matches = re.findall(numbered_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for num, question, answer in matches:
            question = question.strip()
            answer = answer.strip()
            if question and answer:
                qa_pairs.append((question, answer))
        
        return qa_pairs
    
    @staticmethod
    def extract_dialogue_from_text(text: str) -> List[Tuple[str, str]]:
        """Extract dialogue pairs from conversational text."""
        dialogue_pairs = []
        
        # Pattern for Speaker: ... format
        speaker_pattern = r'([A-Z][a-z]+|User|Assistant|Human|AI):\s*(.+?)(?=[A-Z][a-z]+:|User:|Assistant:|Human:|AI:|$)'
        matches = re.findall(speaker_pattern, text, re.DOTALL)
        
        current_user = None
        current_assistant = None
        
        for speaker, content in matches:
            content = content.strip()
            if not content:
                continue
            
            if speaker.lower() in ['user', 'human']:
                if current_assistant and current_user:
                    dialogue_pairs.append((current_user, current_assistant))
                current_user = content
                current_assistant = None
            
            elif speaker.lower() in ['assistant', 'ai']:
                current_assistant = content
                if current_user:
                    dialogue_pairs.append((current_user, current_assistant))
                    current_user = None
                    current_assistant = None
        
        return dialogue_pairs
    
    @staticmethod
    def clean_extracted_text(text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalize quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        
        # Remove URLs and email addresses
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        return text.strip()


# Factory function for creating processors
def create_file_processor(file_path: Path, config: PipelineConfig) -> Optional[FileProcessor]:
    """Create appropriate file processor for the given file."""
    processors = [
        PDFProcessor(config),
        CSVProcessor(config),
        JSONProcessor(config),
        JSONLProcessor(config),
        TextProcessor(config)
    ]
    
    for processor in processors:
        if processor.can_process(file_path):
            return processor
    
    return None
