#!/usr/bin/env python3
"""
Comprehensive quarantine and logging system for suspicious content.
Maintains detailed logs, stores flagged content, and provides analysis tools.
"""

import json
import sqlite3
import hashlib
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import logging
from contextlib import contextmanager


@dataclass
class QuarantineEntry:
    """Represents a quarantined content entry."""
    id: str
    content_hash: str
    original_content: str
    sanitized_content: Optional[str]
    threat_level: str
    threats_detected: List[str]
    source_file: Optional[str]
    timestamp: datetime
    details: Dict[str, Any]
    action_taken: str
    review_status: str = "pending"
    reviewer_notes: Optional[str] = None


class QuarantineDatabase:
    """SQLite database for storing quarantine entries."""
    
    def __init__(self, db_path: str = "quarantine.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize the quarantine database."""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quarantine_entries (
                    id TEXT PRIMARY KEY,
                    content_hash TEXT UNIQUE,
                    original_content_compressed BLOB,
                    sanitized_content_compressed BLOB,
                    threat_level TEXT,
                    threats_detected TEXT,
                    source_file TEXT,
                    timestamp TEXT,
                    details TEXT,
                    action_taken TEXT,
                    review_status TEXT DEFAULT 'pending',
                    reviewer_notes TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON quarantine_entries(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_threat_level ON quarantine_entries(threat_level)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_review_status ON quarantine_entries(review_status)
            """)
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def store_entry(self, entry: QuarantineEntry) -> bool:
        """Store a quarantine entry in the database."""
        try:
            with self.get_connection() as conn:
                # Compress content to save space
                original_compressed = gzip.compress(entry.original_content.encode('utf-8'))
                sanitized_compressed = None
                if entry.sanitized_content:
                    sanitized_compressed = gzip.compress(entry.sanitized_content.encode('utf-8'))
                
                conn.execute("""
                    INSERT OR REPLACE INTO quarantine_entries 
                    (id, content_hash, original_content_compressed, sanitized_content_compressed,
                     threat_level, threats_detected, source_file, timestamp, details, 
                     action_taken, review_status, reviewer_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    entry.content_hash,
                    original_compressed,
                    sanitized_compressed,
                    entry.threat_level,
                    json.dumps(entry.threats_detected),
                    entry.source_file,
                    entry.timestamp.isoformat(),
                    json.dumps(entry.details),
                    entry.action_taken,
                    entry.review_status,
                    entry.reviewer_notes
                ))
                return True
        except Exception as e:
            logging.error(f"Failed to store quarantine entry: {e}")
            return False
    
    def get_entry(self, entry_id: str) -> Optional[QuarantineEntry]:
        """Retrieve a quarantine entry by ID."""
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM quarantine_entries WHERE id = ?", 
                    (entry_id,)
                ).fetchone()
                
                if row:
                    return self._row_to_entry(row)
                return None
        except Exception as e:
            logging.error(f"Failed to retrieve quarantine entry: {e}")
            return None
    
    def search_entries(self, threat_level: str = None, review_status: str = None,
                      start_date: datetime = None, end_date: datetime = None,
                      limit: int = 100) -> List[QuarantineEntry]:
        """Search quarantine entries with filters."""
        query = "SELECT * FROM quarantine_entries WHERE 1=1"
        params = []
        
        if threat_level:
            query += " AND threat_level = ?"
            params.append(threat_level)
        
        if review_status:
            query += " AND review_status = ?"
            params.append(review_status)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            with self.get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                return [self._row_to_entry(row) for row in rows]
        except Exception as e:
            logging.error(f"Failed to search quarantine entries: {e}")
            return []
    
    def update_review_status(self, entry_id: str, status: str, notes: str = None) -> bool:
        """Update the review status of an entry."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE quarantine_entries 
                    SET review_status = ?, reviewer_notes = ?
                    WHERE id = ?
                """, (status, notes, entry_id))
                return True
        except Exception as e:
            logging.error(f"Failed to update review status: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get quarantine database statistics."""
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Total entries
                stats['total_entries'] = conn.execute(
                    "SELECT COUNT(*) FROM quarantine_entries"
                ).fetchone()[0]
                
                # By threat level
                threat_levels = conn.execute("""
                    SELECT threat_level, COUNT(*) 
                    FROM quarantine_entries 
                    GROUP BY threat_level
                """).fetchall()
                stats['by_threat_level'] = dict(threat_levels)
                
                # By review status
                review_statuses = conn.execute("""
                    SELECT review_status, COUNT(*) 
                    FROM quarantine_entries 
                    GROUP BY review_status
                """).fetchall()
                stats['by_review_status'] = dict(review_statuses)
                
                # Recent activity (last 7 days)
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                stats['recent_entries'] = conn.execute(
                    "SELECT COUNT(*) FROM quarantine_entries WHERE timestamp >= ?",
                    (week_ago,)
                ).fetchone()[0]
                
                return stats
        except Exception as e:
            logging.error(f"Failed to get statistics: {e}")
            return {}
    
    def _row_to_entry(self, row) -> QuarantineEntry:
        """Convert database row to QuarantineEntry object."""
        # Decompress content
        original_content = gzip.decompress(row['original_content_compressed']).decode('utf-8')
        sanitized_content = None
        if row['sanitized_content_compressed']:
            sanitized_content = gzip.decompress(row['sanitized_content_compressed']).decode('utf-8')
        
        return QuarantineEntry(
            id=row['id'],
            content_hash=row['content_hash'],
            original_content=original_content,
            sanitized_content=sanitized_content,
            threat_level=row['threat_level'],
            threats_detected=json.loads(row['threats_detected']),
            source_file=row['source_file'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            details=json.loads(row['details']),
            action_taken=row['action_taken'],
            review_status=row['review_status'],
            reviewer_notes=row['reviewer_notes']
        )


class QuarantineLogger:
    """Comprehensive logging system for quarantine operations."""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup different log files
        self.setup_loggers()
    
    def setup_loggers(self):
        """Setup different loggers for different purposes."""
        # Main quarantine logger
        self.quarantine_logger = logging.getLogger('quarantine')
        self.quarantine_logger.setLevel(logging.INFO)
        
        quarantine_handler = logging.FileHandler(self.log_dir / 'quarantine.log')
        quarantine_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        quarantine_handler.setFormatter(quarantine_formatter)
        self.quarantine_logger.addHandler(quarantine_handler)
        
        # Security events logger
        self.security_logger = logging.getLogger('security')
        self.security_logger.setLevel(logging.WARNING)
        
        security_handler = logging.FileHandler(self.log_dir / 'security.log')
        security_formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )
        security_handler.setFormatter(security_formatter)
        self.security_logger.addHandler(security_handler)
        
        # Performance logger
        self.performance_logger = logging.getLogger('performance')
        self.performance_logger.setLevel(logging.INFO)
        
        performance_handler = logging.FileHandler(self.log_dir / 'performance.log')
        performance_formatter = logging.Formatter(
            '%(asctime)s - PERF - %(message)s'
        )
        performance_handler.setFormatter(performance_formatter)
        self.performance_logger.addHandler(performance_handler)
    
    def log_quarantine_action(self, entry: QuarantineEntry):
        """Log a quarantine action."""
        self.quarantine_logger.info(
            f"QUARANTINED - ID: {entry.id}, Threat: {entry.threat_level}, "
            f"Action: {entry.action_taken}, Threats: {', '.join(entry.threats_detected)}"
        )
        
        # Log security events for dangerous threats
        if entry.threat_level in ['dangerous', 'critical']:
            self.security_logger.warning(
                f"HIGH THREAT DETECTED - ID: {entry.id}, Level: {entry.threat_level}, "
                f"Source: {entry.source_file}, Threats: {', '.join(entry.threats_detected)}"
            )
    
    def log_performance_metrics(self, operation: str, duration: float, 
                              items_processed: int = 1):
        """Log performance metrics."""
        self.performance_logger.info(
            f"Operation: {operation}, Duration: {duration:.3f}s, "
            f"Items: {items_processed}, Rate: {items_processed/duration:.2f}/s"
        )
    
    def log_review_action(self, entry_id: str, old_status: str, new_status: str, 
                         reviewer: str = "system"):
        """Log review status changes."""
        self.quarantine_logger.info(
            f"REVIEW UPDATE - ID: {entry_id}, Status: {old_status} -> {new_status}, "
            f"Reviewer: {reviewer}"
        )


class QuarantineManager:
    """Main quarantine management system."""
    
    def __init__(self, db_path: str = "quarantine.db", log_dir: str = "logs"):
        self.database = QuarantineDatabase(db_path)
        self.logger = QuarantineLogger(log_dir)
    
    def quarantine_content(self, content: str, threat_level: str, 
                          threats_detected: List[str], details: Dict[str, Any],
                          source_file: str = None, sanitized_content: str = None,
                          action_taken: str = "quarantined") -> str:
        """Quarantine suspicious content and return entry ID."""
        # Generate unique ID and hash
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        entry_id = f"q_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{content_hash[:8]}"
        
        # Create quarantine entry
        entry = QuarantineEntry(
            id=entry_id,
            content_hash=content_hash,
            original_content=content,
            sanitized_content=sanitized_content,
            threat_level=threat_level,
            threats_detected=threats_detected,
            source_file=source_file,
            timestamp=datetime.now(),
            details=details,
            action_taken=action_taken
        )
        
        # Store in database
        if self.database.store_entry(entry):
            self.logger.log_quarantine_action(entry)
            return entry_id
        else:
            logging.error(f"Failed to quarantine content: {entry_id}")
            return None
    
    def review_entry(self, entry_id: str, status: str, notes: str = None,
                    reviewer: str = "system") -> bool:
        """Review a quarantined entry."""
        entry = self.database.get_entry(entry_id)
        if not entry:
            return False
        
        old_status = entry.review_status
        success = self.database.update_review_status(entry_id, status, notes)
        
        if success:
            self.logger.log_review_action(entry_id, old_status, status, reviewer)
        
        return success
    
    def get_pending_reviews(self, limit: int = 50) -> List[QuarantineEntry]:
        """Get entries pending review."""
        return self.database.search_entries(review_status="pending", limit=limit)
    
    def get_high_threat_entries(self, limit: int = 50) -> List[QuarantineEntry]:
        """Get high threat level entries."""
        dangerous = self.database.search_entries(threat_level="dangerous", limit=limit//2)
        critical = self.database.search_entries(threat_level="critical", limit=limit//2)
        return critical + dangerous
    
    def generate_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive quarantine report."""
        start_date = datetime.now() - timedelta(days=days)
        
        report = {
            'report_period': f"Last {days} days",
            'generated_at': datetime.now().isoformat(),
            'statistics': self.database.get_statistics(),
            'recent_entries': []
        }
        
        # Get recent entries
        recent_entries = self.database.search_entries(
            start_date=start_date, 
            limit=100
        )
        
        for entry in recent_entries:
            report['recent_entries'].append({
                'id': entry.id,
                'timestamp': entry.timestamp.isoformat(),
                'threat_level': entry.threat_level,
                'threats_detected': entry.threats_detected,
                'source_file': entry.source_file,
                'review_status': entry.review_status,
                'content_preview': entry.original_content[:100] + "..." if len(entry.original_content) > 100 else entry.original_content
            })
        
        # Threat analysis
        threat_summary = {}
        for entry in recent_entries:
            for threat in entry.threats_detected:
                threat_summary[threat] = threat_summary.get(threat, 0) + 1
        
        report['threat_analysis'] = {
            'most_common_threats': sorted(threat_summary.items(), key=lambda x: x[1], reverse=True)[:10],
            'unique_threats': len(threat_summary),
            'total_threat_instances': sum(threat_summary.values())
        }
        
        return report
    
    def export_entries(self, output_file: str, threat_level: str = None,
                      review_status: str = None, format: str = "json") -> bool:
        """Export quarantine entries to file."""
        entries = self.database.search_entries(
            threat_level=threat_level,
            review_status=review_status,
            limit=10000  # Large limit for export
        )
        
        try:
            output_path = Path(output_file)
            
            if format.lower() == "json":
                export_data = [asdict(entry) for entry in entries]
                # Convert datetime objects to strings
                for item in export_data:
                    item['timestamp'] = item['timestamp'].isoformat()
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            elif format.lower() == "csv":
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    if entries:
                        writer = csv.DictWriter(f, fieldnames=[
                            'id', 'threat_level', 'threats_detected', 'source_file',
                            'timestamp', 'action_taken', 'review_status'
                        ])
                        writer.writeheader()
                        for entry in entries:
                            writer.writerow({
                                'id': entry.id,
                                'threat_level': entry.threat_level,
                                'threats_detected': ', '.join(entry.threats_detected),
                                'source_file': entry.source_file,
                                'timestamp': entry.timestamp.isoformat(),
                                'action_taken': entry.action_taken,
                                'review_status': entry.review_status
                            })
            
            return True
        except Exception as e:
            logging.error(f"Failed to export entries: {e}")
            return False
    
    def cleanup_old_entries(self, days: int = 90) -> int:
        """Clean up old quarantine entries."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            with self.database.get_connection() as conn:
                result = conn.execute(
                    "DELETE FROM quarantine_entries WHERE timestamp < ? AND review_status = 'approved'",
                    (cutoff_date.isoformat(),)
                )
                deleted_count = result.rowcount
                
                if deleted_count > 0:
                    self.logger.quarantine_logger.info(f"Cleaned up {deleted_count} old entries")
                
                return deleted_count
        except Exception as e:
            logging.error(f"Failed to cleanup old entries: {e}")
            return 0
