#!/usr/bin/env python3
"""
Automated Workflow Orchestrator for the AI-enhanced pipeline.
Manages the complete input → filtered → output workflow with intelligent processing.
"""

import os
import time
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue, Empty

from env_config import get_config, EnvironmentConfig
from pipeline_orchestrator import PipelineOrchestrator, PipelineConfig
from file_processors import create_file_processor
from ai_enhanced_processor import AIEnhancedTextProcessor, ProcessingConfig


@dataclass
class WorkflowStage:
    """Represents a stage in the workflow."""
    name: str
    input_folder: str
    output_folder: str
    processor_type: str
    enabled: bool = True
    parallel: bool = True
    max_workers: int = 4


@dataclass
class WorkflowResult:
    """Result of workflow processing."""
    file_path: str
    stages_completed: List[str]
    stages_failed: List[str]
    total_processing_time: float
    total_cost: float
    final_output_files: List[str]
    success: bool
    error_message: Optional[str] = None


class WorkflowOrchestrator:
    """Main orchestrator for the complete workflow pipeline."""
    
    def __init__(self, config: Optional[EnvironmentConfig] = None):
        self.config = config or get_config()
        self.logger = self._setup_logging()
        
        # Create workflow stages
        self.stages = self._create_workflow_stages()
        
        # Initialize processors
        self.processors = {}
        self._init_processors()
        
        # File monitoring
        self.file_queue = Queue()
        self.processing_queue = Queue()
        self.monitoring_active = False
        
        # Statistics
        self.workflow_stats = {
            'files_processed': 0,
            'files_failed': 0,
            'total_cost': 0.0,
            'average_processing_time': 0.0,
            'stage_stats': {},
            'start_time': datetime.now()
        }
        
        # Create folder structure
        self._create_folder_structure()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the workflow."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config.log_level.upper()))
        
        # File handler if enabled
        if self.config.log_to_file:
            log_file = logs_dir / f"workflow_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
        
        logger.addHandler(console_handler)
        return logger
    
    def _create_workflow_stages(self) -> List[WorkflowStage]:
        """Create the workflow stages."""
        return [
            WorkflowStage(
                name="file_extraction",
                input_folder=self.config.input_folder,
                output_folder=self.config.filtered_folder,
                processor_type="file_processor",
                parallel=self.config.parallel_processing,
                max_workers=self.config.max_workers
            ),
            WorkflowStage(
                name="security_filtering",
                input_folder=self.config.filtered_folder,
                output_folder=self.config.filtered_folder,
                processor_type="security_processor",
                enabled=self.config.enable_security_filtering,
                parallel=True,
                max_workers=self.config.max_workers
            ),
            WorkflowStage(
                name="ai_processing",
                input_folder=self.config.filtered_folder,
                output_folder=self.config.output_folder,
                processor_type="ai_processor",
                enabled=self.config.enable_ai_classification,
                parallel=self.config.parallel_processing,
                max_workers=min(self.config.max_workers, 2)  # Limit AI processing workers
            )
        ]
    
    def _init_processors(self):
        """Initialize all processors."""
        # File processor (handled per file type)
        self.processors['file_processor'] = None
        
        # Security processor
        if self.config.enable_security_filtering:
            try:
                from secure_text_processor import SecureTextProcessor
                self.processors['security_processor'] = SecureTextProcessor(
                    output_format=self.config.output_format,
                    aggressive_mode=(self.config.security_level in ["strict", "paranoid"])
                )
                self.logger.info("Security processor initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize security processor: {e}")
                self.processors['security_processor'] = None
        
        # AI processor
        if self.config.enable_ai_classification and self.config.openai_api_key:
            try:
                ai_config = ProcessingConfig(
                    openai_api_key=self.config.openai_api_key,
                    openai_model=self.config.openai_model,
                    daily_cost_limit=self.config.daily_cost_limit,
                    enable_ai_classification=self.config.enable_ai_classification,
                    enable_content_enhancement=self.config.enable_content_enhancement,
                    enable_security_filtering=False  # Already handled
                )
                
                self.processors['ai_processor'] = AIEnhancedTextProcessor(
                    ai_config, self.config.output_format
                )
                self.logger.info("AI processor initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize AI processor: {e}")
                self.processors['ai_processor'] = None
    
    def _create_folder_structure(self):
        """Create the complete folder structure."""
        folders = [
            self.config.input_folder,
            self.config.filtered_folder,
            self.config.output_folder,
            self.config.error_folder,
            self.config.archive_folder,
            "logs",
            "temp"
        ]
        
        for folder in folders:
            Path(folder).mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created/verified folder: {folder}")
    
    def process_file_through_workflow(self, file_path: Path) -> WorkflowResult:
        """Process a single file through the complete workflow."""
        start_time = time.time()
        
        result = WorkflowResult(
            file_path=str(file_path),
            stages_completed=[],
            stages_failed=[],
            total_processing_time=0.0,
            total_cost=0.0,
            final_output_files=[],
            success=False
        )
        
        current_file_path = file_path
        temp_files = []
        
        try:
            self.logger.info(f"Starting workflow for: {file_path}")
            
            # Process through each stage
            for stage in self.stages:
                if not stage.enabled:
                    self.logger.debug(f"Skipping disabled stage: {stage.name}")
                    continue
                
                stage_start_time = time.time()
                
                try:
                    self.logger.info(f"Processing stage: {stage.name}")
                    
                    # Process file through stage
                    stage_result = self._process_stage(current_file_path, stage)
                    
                    if stage_result['success']:
                        result.stages_completed.append(stage.name)
                        result.total_cost += stage_result.get('cost', 0.0)
                        
                        # Update current file path for next stage
                        if stage_result.get('output_files'):
                            current_file_path = Path(stage_result['output_files'][0])
                            temp_files.extend(stage_result['output_files'][1:])
                        
                        stage_time = time.time() - stage_start_time
                        self.logger.info(f"Stage {stage.name} completed in {stage_time:.2f}s")
                        
                        # Update stage statistics
                        if stage.name not in self.workflow_stats['stage_stats']:
                            self.workflow_stats['stage_stats'][stage.name] = {
                                'processed': 0, 'failed': 0, 'total_time': 0.0
                            }
                        
                        self.workflow_stats['stage_stats'][stage.name]['processed'] += 1
                        self.workflow_stats['stage_stats'][stage.name]['total_time'] += stage_time
                    
                    else:
                        result.stages_failed.append(stage.name)
                        result.error_message = stage_result.get('error', f"Stage {stage.name} failed")
                        
                        # Update failure statistics
                        if stage.name not in self.workflow_stats['stage_stats']:
                            self.workflow_stats['stage_stats'][stage.name] = {
                                'processed': 0, 'failed': 0, 'total_time': 0.0
                            }
                        self.workflow_stats['stage_stats'][stage.name]['failed'] += 1
                        
                        self.logger.error(f"Stage {stage.name} failed: {result.error_message}")
                        break
                
                except Exception as e:
                    result.stages_failed.append(stage.name)
                    result.error_message = f"Stage {stage.name} error: {str(e)}"
                    self.logger.error(f"Stage {stage.name} error: {e}")
                    break
            
            # Check if workflow completed successfully
            if not result.stages_failed and result.stages_completed:
                result.success = True
                result.final_output_files = [str(current_file_path)] + temp_files
                
                # Move original file to archive
                if self.config.auto_move_files:
                    self._archive_file(file_path)
                
                self.logger.info(f"Workflow completed successfully for: {file_path}")
            
            else:
                # Move failed file to error folder
                if self.config.auto_move_files:
                    self._move_to_error_folder(file_path, result.error_message)
                
                self.logger.error(f"Workflow failed for: {file_path}")
        
        except Exception as e:
            result.error_message = f"Workflow error: {str(e)}"
            result.success = False
            self.logger.error(f"Workflow error for {file_path}: {e}")
        
        finally:
            result.total_processing_time = time.time() - start_time
            
            # Update global statistics
            if result.success:
                self.workflow_stats['files_processed'] += 1
            else:
                self.workflow_stats['files_failed'] += 1
            
            self.workflow_stats['total_cost'] += result.total_cost
            
            # Update average processing time
            total_files = self.workflow_stats['files_processed'] + self.workflow_stats['files_failed']
            if total_files > 0:
                total_time = sum(
                    stage_stats['total_time'] 
                    for stage_stats in self.workflow_stats['stage_stats'].values()
                )
                self.workflow_stats['average_processing_time'] = total_time / total_files
        
        return result
    
    def _process_stage(self, file_path: Path, stage: WorkflowStage) -> Dict[str, Any]:
        """Process a file through a specific stage."""
        result = {
            'success': False,
            'output_files': [],
            'cost': 0.0,
            'error': None
        }
        
        try:
            if stage.processor_type == 'file_processor':
                # File extraction stage
                result = self._process_file_extraction(file_path)
            
            elif stage.processor_type == 'security_processor':
                # Security filtering stage
                result = self._process_security_filtering(file_path)
            
            elif stage.processor_type == 'ai_processor':
                # AI processing stage
                result = self._process_ai_enhancement(file_path)
            
            else:
                result['error'] = f"Unknown processor type: {stage.processor_type}"
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _process_file_extraction(self, file_path: Path) -> Dict[str, Any]:
        """Process file extraction stage."""
        result = {'success': False, 'output_files': [], 'cost': 0.0}
        
        try:
            # Get appropriate file processor
            processor = create_file_processor(file_path, self._create_pipeline_config())
            
            if not processor:
                result['error'] = f"No processor available for file type: {file_path.suffix}"
                return result
            
            # Extract text segments
            text_segments = processor.extract_text_segments(file_path)
            
            if not text_segments:
                result['error'] = "No text content extracted"
                return result
            
            # Save extracted text to filtered folder
            output_file = Path(self.config.filtered_folder) / f"{file_path.stem}_extracted.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(text_segments):
                    f.write(f"# Segment {i+1}\n{segment}\n\n")
            
            result['success'] = True
            result['output_files'] = [str(output_file)]
            
            self.logger.info(f"Extracted {len(text_segments)} segments from {file_path}")
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _process_security_filtering(self, file_path: Path) -> Dict[str, Any]:
        """Process security filtering stage."""
        result = {'success': False, 'output_files': [], 'cost': 0.0}
        
        try:
            security_processor = self.processors.get('security_processor')
            
            if not security_processor:
                # Skip security filtering if not available
                result['success'] = True
                result['output_files'] = [str(file_path)]
                return result
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process through security filter
            security_result = security_processor.process_text(content, str(file_path))
            
            if security_result['success']:
                # Save filtered content
                output_file = Path(self.config.filtered_folder) / f"{file_path.stem}_filtered.txt"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(security_result.get('processed_text', content))
                
                result['success'] = True
                result['output_files'] = [str(output_file)]
                
                self.logger.info(f"Security filtering completed for {file_path}")
            
            else:
                result['error'] = f"Security filtering failed: {', '.join(security_result['errors'])}"
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _process_ai_enhancement(self, file_path: Path) -> Dict[str, Any]:
        """Process AI enhancement stage with optional personality modification."""
        result = {'success': False, 'output_files': [], 'cost': 0.0}

        try:
            ai_processor = self.processors.get('ai_processor')

            if not ai_processor:
                # Skip AI processing if not available
                result['success'] = True
                result['output_files'] = [str(file_path)]
                return result

            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Process through AI
            ai_result = ai_processor.process_text(content, str(file_path))

            if ai_result.success:
                processed_content = ai_result.processed_text
                total_cost = ai_result.total_cost

                # Apply personality modification if enabled
                personality_applied = False
                personality_cost = 0.0

                if (hasattr(self.config, 'enable_personality_modifier') and
                    self.config.enable_personality_modifier):

                    try:
                        from personality_modifier import PersonalityModifier

                        personality_modifier = PersonalityModifier()

                        # Get personality settings from config
                        personality_template = getattr(self.config, 'personality_template', 'neutral')
                        personality_strength = getattr(self.config, 'personality_strength', 0.7)
                        custom_personality = getattr(self.config, 'custom_personality', '')

                        # Use custom personality if provided, otherwise use template
                        personality_to_apply = custom_personality if custom_personality else personality_template

                        if personality_to_apply and personality_to_apply != 'neutral':
                            personality_result = personality_modifier.apply_personality(
                                processed_content,
                                personality_to_apply,
                                personality_strength
                            )

                            if personality_result.confidence > 0.5:  # Only apply if confident
                                processed_content = personality_result.modified_text
                                personality_cost = personality_result.cost
                                total_cost += personality_cost
                                personality_applied = True

                                self.logger.info(f"Applied personality '{personality_to_apply}' with strength {personality_strength}")

                    except Exception as e:
                        self.logger.warning(f"Personality modification failed: {e}")

                # Save enhanced content to output folder
                output_file = Path(self.config.output_folder) / f"{file_path.stem}_final.txt"

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(processed_content)

                # Save metadata
                metadata_file = Path(self.config.output_folder) / f"{file_path.stem}_metadata.json"
                metadata = {
                    'original_file': str(file_path),
                    'processed_at': datetime.now().isoformat(),
                    'classification_method': ai_result.classification_method,
                    'classification_confidence': ai_result.classification_confidence,
                    'enhancement_applied': ai_result.enhancement_applied,
                    'personality_applied': personality_applied,
                    'personality_cost': personality_cost,
                    'total_cost': total_cost,
                    'processing_time': ai_result.processing_time
                }

                if personality_applied:
                    metadata['personality_template'] = getattr(self.config, 'personality_template', 'custom')
                    metadata['personality_strength'] = getattr(self.config, 'personality_strength', 0.7)

                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)

                result['success'] = True
                result['output_files'] = [str(output_file), str(metadata_file)]
                result['cost'] = total_cost

                self.logger.info(f"AI processing completed for {file_path}, cost: ${total_cost:.4f}")

            else:
                result['error'] = f"AI processing failed: {', '.join(ai_result.errors)}"

        except Exception as e:
            result['error'] = str(e)

        return result
    
    def _create_pipeline_config(self) -> PipelineConfig:
        """Create pipeline config from environment config."""
        return PipelineConfig(
            input_folder=self.config.input_folder,
            filtered_folder=self.config.filtered_folder,
            output_folder=self.config.output_folder,
            error_folder=self.config.error_folder,
            archive_folder=self.config.archive_folder,
            enable_ai_processing=self.config.enable_ai_classification,
            enable_security_filtering=self.config.enable_security_filtering,
            auto_move_files=self.config.auto_move_files,
            parallel_processing=self.config.parallel_processing,
            max_workers=self.config.max_workers,
            output_format=self.config.output_format,
            openai_api_key=self.config.openai_api_key,
            openai_model=self.config.openai_model,
            daily_cost_limit=self.config.daily_cost_limit
        )
    
    def _archive_file(self, file_path: Path):
        """Move file to archive folder."""
        archive_path = Path(self.config.archive_folder) / file_path.name
        
        # Ensure unique filename
        counter = 1
        while archive_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            archive_path = Path(self.config.archive_folder) / f"{stem}_{counter}{suffix}"
            counter += 1
        
        shutil.move(str(file_path), str(archive_path))
        self.logger.info(f"Archived file: {archive_path}")
    
    def _move_to_error_folder(self, file_path: Path, error_message: str):
        """Move file to error folder with error log."""
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
        supported_extensions = {'.pdf', '.csv', '.json', '.jsonl', '.txt', '.md'}
        files_to_process = [
            f for f in input_path.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
        
        if not files_to_process:
            return {'files_processed': 0, 'files_failed': 0, 'total_cost': 0.0}
        
        self.logger.info(f"Processing {len(files_to_process)} files through workflow")
        
        results = []
        
        if self.config.parallel_processing and len(files_to_process) > 1:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                future_to_file = {
                    executor.submit(self.process_file_through_workflow, file_path): file_path
                    for file_path in files_to_process
                }
                
                for future in as_completed(future_to_file):
                    result = future.result()
                    results.append(result)
        else:
            # Sequential processing
            for file_path in files_to_process:
                result = self.process_file_through_workflow(file_path)
                results.append(result)
        
        # Compile summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_cost = sum(r.total_cost for r in results)
        
        summary = {
            'files_processed': successful,
            'files_failed': failed,
            'total_cost': total_cost,
            'results': results
        }
        
        self.logger.info(f"Workflow batch complete: {successful} successful, {failed} failed, cost: ${total_cost:.4f}")
        
        return summary
    
    def start_monitoring(self):
        """Start monitoring the input folder for new files."""
        self.monitoring_active = True
        self.logger.info("Starting workflow monitoring...")
        
        try:
            while self.monitoring_active:
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
        finally:
            self.monitoring_active = False
    
    def stop_monitoring(self):
        """Stop the monitoring process."""
        self.monitoring_active = False
        self.logger.info("Stopping workflow monitoring...")
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get comprehensive workflow status."""
        # Count files in each folder
        folder_counts = {}
        for folder_name in ['input_folder', 'filtered_folder', 'output_folder', 'error_folder', 'archive_folder']:
            folder_path = Path(getattr(self.config, folder_name))
            folder_counts[folder_name] = len(list(folder_path.glob('*'))) if folder_path.exists() else 0
        
        # Calculate runtime
        runtime = datetime.now() - self.workflow_stats['start_time']
        
        return {
            'workflow_status': {
                'monitoring_active': self.monitoring_active,
                'folder_counts': folder_counts,
                'enabled_stages': [stage.name for stage in self.stages if stage.enabled]
            },
            'processing_statistics': self.workflow_stats,
            'runtime': str(runtime),
            'configuration': {
                'ai_processing': self.config.enable_ai_classification,
                'content_enhancement': self.config.enable_content_enhancement,
                'security_filtering': self.config.enable_security_filtering,
                'parallel_processing': self.config.parallel_processing,
                'output_format': self.config.output_format,
                'daily_cost_limit': self.config.daily_cost_limit
            }
        }
