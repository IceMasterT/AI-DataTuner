#!/usr/bin/env python3
"""
File monitoring and automatic movement system for the pipeline.
Watches folders for new files and triggers processing automatically.
"""

import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable, Set
from dataclasses import dataclass
from datetime import datetime
import logging
from queue import Queue, Empty
import hashlib

from env_config import get_config, EnvironmentConfig


@dataclass
class FileEvent:
    """Represents a file system event."""
    event_type: str  # 'created', 'modified', 'deleted', 'moved'
    file_path: Path
    timestamp: datetime
    file_size: int = 0
    file_hash: Optional[str] = None


@dataclass
class MonitoredFolder:
    """Configuration for a monitored folder."""
    path: Path
    watch_patterns: List[str]  # File patterns to watch
    ignore_patterns: List[str]  # Patterns to ignore
    callback: Optional[Callable] = None
    recursive: bool = False
    enabled: bool = True


class FileHashTracker:
    """Tracks file hashes to detect actual changes vs. timestamp updates."""
    
    def __init__(self):
        self.file_hashes: Dict[str, str] = {}
        self.logger = logging.getLogger(f"{__name__}.FileHashTracker")
    
    def get_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculate MD5 hash of file content."""
        try:
            if not file_path.exists() or not file_path.is_file():
                return None
            
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            return hash_md5.hexdigest()
        
        except Exception as e:
            self.logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return None
    
    def has_file_changed(self, file_path: Path) -> bool:
        """Check if file content has actually changed."""
        current_hash = self.get_file_hash(file_path)
        if current_hash is None:
            return False
        
        file_key = str(file_path)
        previous_hash = self.file_hashes.get(file_key)
        
        if previous_hash != current_hash:
            self.file_hashes[file_key] = current_hash
            return True
        
        return False
    
    def track_file(self, file_path: Path):
        """Start tracking a file."""
        file_hash = self.get_file_hash(file_path)
        if file_hash:
            self.file_hashes[str(file_path)] = file_hash
    
    def untrack_file(self, file_path: Path):
        """Stop tracking a file."""
        file_key = str(file_path)
        if file_key in self.file_hashes:
            del self.file_hashes[file_key]


class SimpleFileMonitor:
    """Simple file monitoring using polling (cross-platform)."""
    
    def __init__(self, config: EnvironmentConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.monitored_folders: Dict[str, MonitoredFolder] = {}
        self.file_tracker = FileHashTracker()
        self.event_queue = Queue()
        self.monitoring_active = False
        self.monitor_thread = None
        
        # File state tracking
        self.known_files: Dict[str, Dict] = {}  # path -> {size, mtime, hash}
        self.processing_files: Set[str] = set()  # Files currently being processed
        
        # Setup default monitored folders
        self._setup_default_monitors()
    
    def _setup_default_monitors(self):
        """Setup default folder monitoring."""
        # Monitor input folder for new files
        self.add_monitored_folder(
            name="input",
            path=Path(self.config.input_folder),
            watch_patterns=["*.pdf", "*.csv", "*.json", "*.jsonl", "*.txt", "*.md"],
            ignore_patterns=[".*", "*.tmp", "*.lock"],
            callback=self._handle_input_file_event
        )
        
        # Monitor filtered folder for intermediate files
        self.add_monitored_folder(
            name="filtered",
            path=Path(self.config.filtered_folder),
            watch_patterns=["*.txt", "*.json"],
            ignore_patterns=[".*", "*.tmp", "*.lock"],
            callback=self._handle_filtered_file_event
        )
    
    def add_monitored_folder(self, name: str, path: Path, watch_patterns: List[str],
                           ignore_patterns: List[str] = None, callback: Callable = None):
        """Add a folder to monitor."""
        if ignore_patterns is None:
            ignore_patterns = []
        
        # Create folder if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)
        
        monitor = MonitoredFolder(
            path=path,
            watch_patterns=watch_patterns,
            ignore_patterns=ignore_patterns,
            callback=callback,
            recursive=False,
            enabled=True
        )
        
        self.monitored_folders[name] = monitor
        self.logger.info(f"Added monitored folder: {name} -> {path}")
        
        # Initialize known files for this folder
        self._scan_folder_initial(monitor)
    
    def _scan_folder_initial(self, monitor: MonitoredFolder):
        """Initial scan of a folder to establish baseline."""
        try:
            for file_path in monitor.path.iterdir():
                if file_path.is_file() and self._should_monitor_file(file_path, monitor):
                    file_info = self._get_file_info(file_path)
                    self.known_files[str(file_path)] = file_info
                    self.file_tracker.track_file(file_path)
        
        except Exception as e:
            self.logger.warning(f"Error scanning folder {monitor.path}: {e}")
    
    def _should_monitor_file(self, file_path: Path, monitor: MonitoredFolder) -> bool:
        """Check if a file should be monitored based on patterns."""
        file_name = file_path.name
        
        # Check ignore patterns first
        for pattern in monitor.ignore_patterns:
            if self._match_pattern(file_name, pattern):
                return False
        
        # Check watch patterns
        for pattern in monitor.watch_patterns:
            if self._match_pattern(file_name, pattern):
                return True
        
        return False
    
    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)."""
        if pattern == "*":
            return True
        
        if "*" not in pattern:
            return filename == pattern
        
        # Simple wildcard matching
        if pattern.startswith("*."):
            extension = pattern[2:]
            return filename.endswith(f".{extension}")
        
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return filename.startswith(prefix)
        
        return filename == pattern
    
    def _get_file_info(self, file_path: Path) -> Dict:
        """Get file information for change detection."""
        try:
            stat = file_path.stat()
            return {
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'exists': True
            }
        except Exception:
            return {'size': 0, 'mtime': 0, 'exists': False}
    
    def start_monitoring(self):
        """Start file monitoring."""
        if self.monitoring_active:
            self.logger.warning("Monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("File monitoring started")
    
    def stop_monitoring(self):
        """Stop file monitoring."""
        self.monitoring_active = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("File monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                self._check_all_folders()
                time.sleep(self.config.file_check_interval)
            
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1.0)  # Brief pause on error
    
    def _check_all_folders(self):
        """Check all monitored folders for changes."""
        for name, monitor in self.monitored_folders.items():
            if not monitor.enabled:
                continue
            
            try:
                self._check_folder(monitor)
            except Exception as e:
                self.logger.error(f"Error checking folder {name}: {e}")
    
    def _check_folder(self, monitor: MonitoredFolder):
        """Check a specific folder for file changes."""
        if not monitor.path.exists():
            return
        
        current_files = set()
        
        # Check existing files
        for file_path in monitor.path.iterdir():
            if not file_path.is_file():
                continue
            
            file_str = str(file_path)
            current_files.add(file_str)
            
            if not self._should_monitor_file(file_path, monitor):
                continue
            
            # Skip files currently being processed
            if file_str in self.processing_files:
                continue
            
            current_info = self._get_file_info(file_path)
            
            if file_str not in self.known_files:
                # New file detected
                self.known_files[file_str] = current_info
                self.file_tracker.track_file(file_path)
                
                # Wait a moment to ensure file is fully written
                time.sleep(0.5)
                
                # Check if file is still being written
                if self._is_file_stable(file_path):
                    event = FileEvent(
                        event_type='created',
                        file_path=file_path,
                        timestamp=datetime.now(),
                        file_size=current_info['size']
                    )
                    self._handle_file_event(event, monitor)
            
            else:
                # Check for modifications
                previous_info = self.known_files[file_str]
                
                if (current_info['size'] != previous_info['size'] or 
                    current_info['mtime'] != previous_info['mtime']):
                    
                    # File potentially modified, check content hash
                    if self.file_tracker.has_file_changed(file_path):
                        self.known_files[file_str] = current_info
                        
                        # Wait for file stability
                        if self._is_file_stable(file_path):
                            event = FileEvent(
                                event_type='modified',
                                file_path=file_path,
                                timestamp=datetime.now(),
                                file_size=current_info['size']
                            )
                            self._handle_file_event(event, monitor)
        
        # Check for deleted files
        for file_str in list(self.known_files.keys()):
            if file_str not in current_files:
                file_path = Path(file_str)
                
                if self._should_monitor_file(file_path, monitor):
                    del self.known_files[file_str]
                    self.file_tracker.untrack_file(file_path)
                    
                    event = FileEvent(
                        event_type='deleted',
                        file_path=file_path,
                        timestamp=datetime.now()
                    )
                    self._handle_file_event(event, monitor)
    
    def _is_file_stable(self, file_path: Path, stability_time: float = 1.0) -> bool:
        """Check if file is stable (not being written to)."""
        try:
            initial_info = self._get_file_info(file_path)
            time.sleep(stability_time)
            final_info = self._get_file_info(file_path)
            
            return (initial_info['size'] == final_info['size'] and 
                   initial_info['mtime'] == final_info['mtime'])
        
        except Exception:
            return False
    
    def _handle_file_event(self, event: FileEvent, monitor: MonitoredFolder):
        """Handle a file system event."""
        self.logger.info(f"File event: {event.event_type} - {event.file_path}")
        
        # Add to event queue
        self.event_queue.put((event, monitor))
        
        # Call monitor callback if available
        if monitor.callback:
            try:
                monitor.callback(event)
            except Exception as e:
                self.logger.error(f"Error in monitor callback: {e}")
    
    def _handle_input_file_event(self, event: FileEvent):
        """Handle events in the input folder."""
        if event.event_type == 'created':
            self.logger.info(f"New input file detected: {event.file_path}")
            
            # Mark file as being processed
            self.processing_files.add(str(event.file_path))
            
            # Trigger processing (this would be connected to the workflow orchestrator)
            self._trigger_file_processing(event.file_path)
    
    def _handle_filtered_file_event(self, event: FileEvent):
        """Handle events in the filtered folder."""
        if event.event_type == 'created':
            self.logger.info(f"New filtered file detected: {event.file_path}")
            # Could trigger next stage of processing
    
    def _trigger_file_processing(self, file_path: Path):
        """Trigger processing for a new file."""
        # This would integrate with the workflow orchestrator
        self.logger.info(f"Triggering processing for: {file_path}")
        
        # For now, just log the event
        # In a full implementation, this would:
        # 1. Validate the file
        # 2. Check file size limits
        # 3. Queue for processing
        # 4. Start workflow orchestrator if not running
    
    def mark_file_processing_complete(self, file_path: Path):
        """Mark a file as processing complete."""
        file_str = str(file_path)
        if file_str in self.processing_files:
            self.processing_files.remove(file_str)
            self.logger.info(f"File processing completed: {file_path}")
    
    def get_pending_events(self, max_events: int = 10) -> List[tuple]:
        """Get pending file events from the queue."""
        events = []
        
        for _ in range(max_events):
            try:
                event_data = self.event_queue.get_nowait()
                events.append(event_data)
            except Empty:
                break
        
        return events
    
    def get_monitoring_status(self) -> Dict:
        """Get current monitoring status."""
        return {
            'monitoring_active': self.monitoring_active,
            'monitored_folders': {
                name: {
                    'path': str(monitor.path),
                    'enabled': monitor.enabled,
                    'watch_patterns': monitor.watch_patterns,
                    'file_count': len(list(monitor.path.glob('*'))) if monitor.path.exists() else 0
                }
                for name, monitor in self.monitored_folders.items()
            },
            'known_files_count': len(self.known_files),
            'processing_files_count': len(self.processing_files),
            'pending_events': self.event_queue.qsize()
        }


class FileMovementManager:
    """Manages automatic file movement between pipeline stages."""
    
    def __init__(self, config: EnvironmentConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.FileMovementManager")
    
    def move_file_safely(self, source_path: Path, destination_path: Path, 
                        create_backup: bool = True) -> bool:
        """Safely move a file with error handling and backup."""
        try:
            # Ensure destination directory exists
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle existing destination file
            if destination_path.exists():
                if create_backup:
                    backup_path = self._create_backup_path(destination_path)
                    destination_path.rename(backup_path)
                    self.logger.info(f"Created backup: {backup_path}")
                else:
                    destination_path.unlink()
            
            # Move the file
            source_path.rename(destination_path)
            self.logger.info(f"Moved file: {source_path} -> {destination_path}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to move file {source_path} -> {destination_path}: {e}")
            return False
    
    def _create_backup_path(self, file_path: Path) -> Path:
        """Create a unique backup path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
        return file_path.parent / backup_name
    
    def cleanup_empty_folders(self, folder_path: Path):
        """Remove empty folders recursively."""
        try:
            if folder_path.exists() and folder_path.is_dir():
                # Remove empty subdirectories first
                for subfolder in folder_path.iterdir():
                    if subfolder.is_dir():
                        self.cleanup_empty_folders(subfolder)
                
                # Remove this folder if it's empty
                if not any(folder_path.iterdir()):
                    folder_path.rmdir()
                    self.logger.debug(f"Removed empty folder: {folder_path}")
        
        except Exception as e:
            self.logger.warning(f"Could not cleanup folder {folder_path}: {e}")


# Factory function for creating file monitor
def create_file_monitor(config: Optional[EnvironmentConfig] = None) -> SimpleFileMonitor:
    """Create and configure a file monitor."""
    if config is None:
        config = get_config()
    
    return SimpleFileMonitor(config)
