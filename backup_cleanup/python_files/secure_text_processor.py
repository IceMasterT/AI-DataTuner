#!/usr/bin/env python3
"""
Secure text processor that integrates sanitization with existing text formatting pipeline.
Provides a secure wrapper around the text formatter with comprehensive threat detection.
"""

import time
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

from text_formatter import ConversationFormatter
from sanitization_engine import CoreSanitizer, SanitizationResult, ThreatLevel
from advanced_detectors import AdvancedThreatDetector
from markup_validators import MarkupValidator
from quarantine_system import QuarantineManager
from format_templates import ConversationFormat


class SecureTextProcessor:
    """Secure text processor with integrated sanitization."""
    
    def __init__(self, output_format: str = "qwen", aggressive_mode: bool = False,
                 quarantine_enabled: bool = True, **format_kwargs):
        # Initialize components
        self.formatter = ConversationFormatter(output_format, **format_kwargs)
        self.core_sanitizer = CoreSanitizer()
        self.advanced_detector = AdvancedThreatDetector()
        self.markup_validator = MarkupValidator()
        
        # Configuration
        self.aggressive_mode = aggressive_mode
        self.quarantine_enabled = quarantine_enabled
        
        # Initialize quarantine system if enabled
        if self.quarantine_enabled:
            self.quarantine_manager = QuarantineManager()
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'clean_content': 0,
            'sanitized_content': 0,
            'quarantined_content': 0,
            'rejected_content': 0,
            'processing_time': 0.0
        }
    
    def process_text(self, text: str, source_file: str = None, 
                    validate_markup: bool = True) -> Dict[str, Any]:
        """
        Process text with comprehensive security checks.
        
        Args:
            text: Input text to process
            source_file: Source file path for logging
            validate_markup: Whether to validate markup content
            
        Returns:
            Processing result with sanitized/formatted text and security info
        """
        start_time = time.time()
        
        result = {
            'success': False,
            'original_text': text,
            'processed_text': None,
            'security_analysis': {},
            'action_taken': 'unknown',
            'quarantine_id': None,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Step 1: Core sanitization
            sanitization_result = self.core_sanitizer.sanitize_text(text, self.aggressive_mode)
            result['security_analysis']['core_sanitization'] = {
                'threat_level': sanitization_result.threat_level.value,
                'threats_detected': [t.value for t in sanitization_result.threats_detected],
                'details': sanitization_result.details,
                'action_taken': sanitization_result.action_taken
            }
            
            # Step 2: Advanced threat detection
            if sanitization_result.threat_level != ThreatLevel.CLEAN:
                advanced_analysis = self.advanced_detector.comprehensive_threat_analysis(text)
                result['security_analysis']['advanced_analysis'] = advanced_analysis
            
            # Step 3: Markup validation (if requested and content looks like markup)
            if validate_markup and self._looks_like_markup(text):
                markup_analysis = self._validate_markup_content(text)
                result['security_analysis']['markup_validation'] = markup_analysis
            
            # Step 4: Determine final action
            final_action = self._determine_final_action(sanitization_result, result['security_analysis'])
            result['action_taken'] = final_action
            
            # Step 5: Handle based on action
            if final_action == 'accept':
                # Process with formatter
                processed_text = self._safe_format_text(sanitization_result.sanitized_text or text)
                result['processed_text'] = processed_text
                result['success'] = True
                self.stats['clean_content'] += 1
                
            elif final_action == 'accept_with_warning':
                # Process but add warnings
                processed_text = self._safe_format_text(sanitization_result.sanitized_text or text)
                result['processed_text'] = processed_text
                result['success'] = True
                result['warnings'].append("Content processed with security warnings")
                self.stats['sanitized_content'] += 1
                
            elif final_action == 'quarantine':
                # Quarantine the content
                if self.quarantine_enabled:
                    quarantine_id = self._quarantine_content(
                        text, sanitization_result, source_file, result['security_analysis']
                    )
                    result['quarantine_id'] = quarantine_id
                
                result['errors'].append("Content quarantined due to security concerns")
                self.stats['quarantined_content'] += 1
                
            elif final_action == 'reject':
                # Reject the content
                result['errors'].append("Content rejected due to high security risk")
                self.stats['rejected_content'] += 1
            
            # Update statistics
            self.stats['total_processed'] += 1
            processing_time = time.time() - start_time
            self.stats['processing_time'] += processing_time
            
            # Log performance if quarantine system is available
            if self.quarantine_enabled:
                self.quarantine_manager.logger.log_performance_metrics(
                    'secure_text_processing', processing_time
                )
            
        except Exception as e:
            result['errors'].append(f"Processing error: {str(e)}")
            result['action_taken'] = 'error'
        
        return result
    
    def batch_process(self, input_files: List[str], output_dir: str = None,
                     **kwargs) -> Dict[str, Any]:
        """
        Securely process multiple files in batch.
        
        Args:
            input_files: List of input file paths
            output_dir: Output directory for processed files
            **kwargs: Additional arguments for processing
            
        Returns:
            Batch processing results
        """
        results = {
            'total_files': len(input_files),
            'successful': 0,
            'failed': 0,
            'quarantined': 0,
            'rejected': 0,
            'file_results': [],
            'security_summary': {}
        }
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        
        for input_file in input_files:
            try:
                # Read input file
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Process content
                process_result = self.process_text(content, source_file=input_file, **kwargs)
                
                file_result = {
                    'input_file': input_file,
                    'success': process_result['success'],
                    'action_taken': process_result['action_taken'],
                    'quarantine_id': process_result.get('quarantine_id'),
                    'warnings': process_result['warnings'],
                    'errors': process_result['errors']
                }
                
                # Save processed content if successful
                if process_result['success'] and process_result['processed_text'] and output_dir:
                    input_path = Path(input_file)
                    output_file = output_path / f"{input_path.stem}_secure{input_path.suffix}"
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(process_result['processed_text'])
                    
                    file_result['output_file'] = str(output_file)
                
                # Update counters
                if process_result['success']:
                    results['successful'] += 1
                elif process_result['action_taken'] == 'quarantine':
                    results['quarantined'] += 1
                elif process_result['action_taken'] == 'reject':
                    results['rejected'] += 1
                else:
                    results['failed'] += 1
                
                results['file_results'].append(file_result)
                
            except Exception as e:
                results['failed'] += 1
                results['file_results'].append({
                    'input_file': input_file,
                    'success': False,
                    'action_taken': 'error',
                    'errors': [f"File processing error: {str(e)}"]
                })
        
        # Generate security summary
        results['security_summary'] = self.get_processing_statistics()
        
        return results
    
    def _looks_like_markup(self, text: str) -> bool:
        """Check if text looks like markup content."""
        markup_indicators = ['<', '>', '{', '}', '[', ']', '```', '---']
        return any(indicator in text for indicator in markup_indicators)
    
    def _validate_markup_content(self, text: str) -> Dict[str, Any]:
        """Validate markup content using appropriate validator."""
        validation_results = {}
        
        # Try different markup types
        if '<' in text and '>' in text:
            # Looks like HTML/XML
            if '<!DOCTYPE' in text.upper() or '<html' in text.lower():
                validation_results['html'] = self.markup_validator.validate_html(text)
            else:
                validation_results['xml'] = self.markup_validator.validate_xml(text)
        
        if text.strip().startswith('{') or text.strip().startswith('['):
            # Looks like JSON
            validation_results['json'] = self.markup_validator.validate_json(text)
        
        if '```' in text or '#' in text:
            # Looks like Markdown
            validation_results['markdown'] = self.markup_validator.validate_markdown(text)
        
        # Check for code content
        if any(keyword in text for keyword in ['def ', 'function ', 'SELECT ', 'import ']):
            validation_results['code'] = self.markup_validator.validate_code(text)
        
        return validation_results
    
    def _determine_final_action(self, sanitization_result: SanitizationResult,
                               security_analysis: Dict[str, Any]) -> str:
        """Determine final action based on all security analyses."""
        # Start with core sanitization action
        base_action = sanitization_result.action_taken
        
        # Check advanced analysis if available
        if 'advanced_analysis' in security_analysis:
            threat_score = security_analysis['advanced_analysis'].get('threat_score', 0)
            threat_level = security_analysis['advanced_analysis'].get('threat_level', 'low')
            
            if threat_level == 'critical' or threat_score > 80:
                return 'reject'
            elif threat_level == 'high' or threat_score > 50:
                return 'quarantine'
        
        # Check markup validation if available
        if 'markup_validation' in security_analysis:
            for format_name, validation in security_analysis['markup_validation'].items():
                if validation.get('security_issues'):
                    if self.aggressive_mode:
                        return 'quarantine'
                    else:
                        base_action = 'accept_with_warning'
        
        return base_action
    
    def _safe_format_text(self, text: str) -> str:
        """Safely format text using the conversation formatter."""
        try:
            return self.formatter.process_text(text)
        except Exception as e:
            # If formatting fails, return sanitized text with error note
            return f"[FORMATTING ERROR: {str(e)}]\n\n{text}"
    
    def _quarantine_content(self, original_text: str, sanitization_result: SanitizationResult,
                           source_file: str, security_analysis: Dict[str, Any]) -> Optional[str]:
        """Quarantine suspicious content."""
        if not self.quarantine_enabled:
            return None
        
        # Prepare quarantine details
        details = {
            'sanitization_details': sanitization_result.details,
            'security_analysis': security_analysis,
            'processing_mode': 'aggressive' if self.aggressive_mode else 'normal'
        }
        
        # Quarantine the content
        quarantine_id = self.quarantine_manager.quarantine_content(
            content=original_text,
            threat_level=sanitization_result.threat_level.value,
            threats_detected=[t.value for t in sanitization_result.threats_detected],
            details=details,
            source_file=source_file,
            sanitized_content=sanitization_result.sanitized_text,
            action_taken='quarantined'
        )
        
        return quarantine_id
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        total = self.stats['total_processed']
        if total == 0:
            return self.stats.copy()
        
        stats = self.stats.copy()
        stats['success_rate'] = (self.stats['clean_content'] + self.stats['sanitized_content']) / total * 100
        stats['quarantine_rate'] = self.stats['quarantined_content'] / total * 100
        stats['rejection_rate'] = self.stats['rejected_content'] / total * 100
        stats['avg_processing_time'] = self.stats['processing_time'] / total
        
        return stats
    
    def generate_security_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        if not self.quarantine_enabled:
            return {'error': 'Quarantine system not enabled'}
        
        # Get quarantine report
        quarantine_report = self.quarantine_manager.generate_report(days)
        
        # Add processing statistics
        report = {
            'quarantine_data': quarantine_report,
            'processing_statistics': self.get_processing_statistics(),
            'configuration': {
                'aggressive_mode': self.aggressive_mode,
                'quarantine_enabled': self.quarantine_enabled,
                'output_format': self.formatter.output_format
            }
        }
        
        return report
    
    def review_quarantined_content(self, entry_id: str, action: str, 
                                  notes: str = None) -> bool:
        """Review quarantined content."""
        if not self.quarantine_enabled:
            return False
        
        return self.quarantine_manager.review_entry(entry_id, action, notes)
    
    def get_quarantine_queue(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending quarantine reviews."""
        if not self.quarantine_enabled:
            return []
        
        entries = self.quarantine_manager.get_pending_reviews(limit)
        
        # Convert to simplified format for review
        queue = []
        for entry in entries:
            queue.append({
                'id': entry.id,
                'timestamp': entry.timestamp.isoformat(),
                'threat_level': entry.threat_level,
                'threats_detected': entry.threats_detected,
                'source_file': entry.source_file,
                'content_preview': entry.original_content[:200] + "..." if len(entry.original_content) > 200 else entry.original_content,
                'details': entry.details
            })
        
        return queue
