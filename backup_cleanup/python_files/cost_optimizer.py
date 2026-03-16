#!/usr/bin/env python3
"""
Cost optimization system for OpenAI API usage.
Implements intelligent caching, batching, and cost monitoring.
"""

import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from collections import defaultdict


@dataclass
class CostMetrics:
    """Cost tracking metrics."""
    total_cost: float
    total_tokens: int
    total_requests: int
    cache_hits: int
    cache_misses: int
    cost_saved_by_cache: float
    average_cost_per_request: float
    average_tokens_per_request: float


@dataclass
class OptimizationRecommendation:
    """Cost optimization recommendation."""
    type: str
    description: str
    potential_savings: float
    implementation_effort: str  # "low", "medium", "high"
    priority: str  # "low", "medium", "high"


class IntelligentCache:
    """Advanced caching system with cost optimization."""
    
    def __init__(self, cache_file: str = "intelligent_cache.db"):
        self.cache_file = Path(cache_file)
        self.init_cache()
        self.cache_stats = defaultdict(int)
    
    def init_cache(self):
        """Initialize cache database with advanced features."""
        with sqlite3.connect(self.cache_file) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    content_hash TEXT,
                    prompt_type TEXT,
                    model TEXT,
                    response TEXT,
                    tokens_input INTEGER,
                    tokens_output INTEGER,
                    cost REAL,
                    quality_score REAL,
                    usage_count INTEGER DEFAULT 1,
                    last_used TEXT,
                    created_at TEXT,
                    expires_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_analytics (
                    date TEXT PRIMARY KEY,
                    total_requests INTEGER,
                    cache_hits INTEGER,
                    cache_misses INTEGER,
                    cost_saved REAL,
                    storage_size_mb REAL
                )
            """)
            
            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON cache_entries(content_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_count ON cache_entries(usage_count)")
    
    def get_cache_key(self, prompt: str, model: str, prompt_type: str = "general", **kwargs) -> str:
        """Generate intelligent cache key."""
        # Normalize prompt for better cache hits
        normalized_prompt = self._normalize_prompt(prompt)
        
        cache_data = {
            "prompt": normalized_prompt,
            "model": model,
            "type": prompt_type,
            **kwargs
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    def _normalize_prompt(self, prompt: str) -> str:
        """Normalize prompt for better cache efficiency."""
        # Remove extra whitespace
        normalized = " ".join(prompt.split())
        
        # Convert to lowercase for classification tasks
        if len(normalized) < 200:  # Short prompts are likely classification
            normalized = normalized.lower()
        
        return normalized
    
    def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response with usage tracking."""
        with sqlite3.connect(self.cache_file) as conn:
            conn.row_factory = sqlite3.Row
            
            row = conn.execute("""
                SELECT * FROM cache_entries 
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat())).fetchone()
            
            if row:
                # Update usage statistics
                conn.execute("""
                    UPDATE cache_entries 
                    SET usage_count = usage_count + 1, last_used = ?
                    WHERE cache_key = ?
                """, (datetime.now().isoformat(), cache_key))
                
                self.cache_stats['hits'] += 1
                
                return {
                    "response": row["response"],
                    "tokens_input": row["tokens_input"],
                    "tokens_output": row["tokens_output"],
                    "cost": row["cost"],
                    "quality_score": row["quality_score"],
                    "cached": True,
                    "usage_count": row["usage_count"] + 1
                }
        
        self.cache_stats['misses'] += 1
        return None
    
    def cache_response(self, cache_key: str, prompt: str, model: str, response: str,
                      tokens_input: int, tokens_output: int, cost: float,
                      prompt_type: str = "general", quality_score: float = 0.8,
                      cache_duration_hours: int = 24):
        """Cache response with metadata."""
        content_hash = hashlib.sha256(prompt.encode()).hexdigest()
        expires_at = datetime.now() + timedelta(hours=cache_duration_hours)
        
        with sqlite3.connect(self.cache_file) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries 
                (cache_key, content_hash, prompt_type, model, response, 
                 tokens_input, tokens_output, cost, quality_score, 
                 last_used, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key, content_hash, prompt_type, model, response,
                tokens_input, tokens_output, cost, quality_score,
                datetime.now().isoformat(), datetime.now().isoformat(),
                expires_at.isoformat()
            ))
    
    def get_cache_analytics(self) -> Dict[str, Any]:
        """Get comprehensive cache analytics."""
        with sqlite3.connect(self.cache_file) as conn:
            conn.row_factory = sqlite3.Row
            
            # Overall statistics
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(usage_count) as total_usage,
                    SUM(cost) as total_cost_cached,
                    AVG(quality_score) as avg_quality,
                    COUNT(CASE WHEN expires_at > ? THEN 1 END) as active_entries
                FROM cache_entries
            """, (datetime.now().isoformat(),)).fetchone()
            
            # Most used entries
            popular_entries = conn.execute("""
                SELECT prompt_type, model, usage_count, cost
                FROM cache_entries 
                WHERE expires_at > ?
                ORDER BY usage_count DESC 
                LIMIT 10
            """, (datetime.now().isoformat(),)).fetchall()
            
            # Daily analytics
            daily_stats = conn.execute("""
                SELECT * FROM cache_analytics 
                ORDER BY date DESC 
                LIMIT 7
            """).fetchall()
            
            return {
                "overall": dict(stats) if stats else {},
                "popular_entries": [dict(row) for row in popular_entries],
                "daily_stats": [dict(row) for row in daily_stats],
                "current_session": {
                    "hits": self.cache_stats['hits'],
                    "misses": self.cache_stats['misses'],
                    "hit_rate": self.cache_stats['hits'] / max(1, self.cache_stats['hits'] + self.cache_stats['misses'])
                }
            }
    
    def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache by removing low-value entries."""
        with sqlite3.connect(self.cache_file) as conn:
            # Remove expired entries
            expired_count = conn.execute("""
                DELETE FROM cache_entries WHERE expires_at < ?
            """, (datetime.now().isoformat(),)).rowcount
            
            # Remove low-usage, low-quality entries if cache is large
            total_entries = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
            
            removed_low_value = 0
            if total_entries > 10000:  # If cache is getting large
                removed_low_value = conn.execute("""
                    DELETE FROM cache_entries 
                    WHERE usage_count = 1 AND quality_score < 0.5 
                    AND created_at < ?
                """, ((datetime.now() - timedelta(days=7)).isoformat(),)).rowcount
            
            return {
                "expired_removed": expired_count,
                "low_value_removed": removed_low_value,
                "total_entries_after": total_entries - expired_count - removed_low_value
            }


class BatchProcessor:
    """Intelligent batching for cost optimization."""
    
    def __init__(self, batch_size: int = 5, batch_timeout: float = 2.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests = []
        self.last_batch_time = time.time()
    
    def add_request(self, request_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Add request to batch and return batch if ready."""
        self.pending_requests.append(request_data)
        
        # Check if batch is ready
        if (len(self.pending_requests) >= self.batch_size or 
            time.time() - self.last_batch_time > self.batch_timeout):
            return self.flush_batch()
        
        return None
    
    def flush_batch(self) -> List[Dict[str, Any]]:
        """Flush current batch and return requests."""
        if not self.pending_requests:
            return []
        
        batch = self.pending_requests.copy()
        self.pending_requests.clear()
        self.last_batch_time = time.time()
        
        return batch
    
    def optimize_batch_order(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize batch order for better caching."""
        # Group similar requests together
        classification_requests = []
        enhancement_requests = []
        other_requests = []
        
        for req in requests:
            req_type = req.get('type', 'other')
            if req_type == 'classification':
                classification_requests.append(req)
            elif req_type == 'enhancement':
                enhancement_requests.append(req)
            else:
                other_requests.append(req)
        
        # Return grouped requests
        return classification_requests + enhancement_requests + other_requests


class CostMonitor:
    """Real-time cost monitoring and alerting."""
    
    def __init__(self, daily_limit: float = 10.0, alert_thresholds: List[float] = None):
        self.daily_limit = daily_limit
        self.alert_thresholds = alert_thresholds or [0.5, 0.8, 0.9]  # 50%, 80%, 90%
        self.cost_file = Path("daily_costs.json")
        self.alerts_sent = set()
    
    def track_cost(self, cost: float, tokens: int, model: str):
        """Track API cost and check limits."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Load existing costs
        costs = self._load_costs()
        
        # Update today's costs
        if today not in costs:
            costs[today] = {"total_cost": 0.0, "total_tokens": 0, "requests": 0, "models": {}}
        
        costs[today]["total_cost"] += cost
        costs[today]["total_tokens"] += tokens
        costs[today]["requests"] += 1
        
        if model not in costs[today]["models"]:
            costs[today]["models"][model] = {"cost": 0.0, "tokens": 0, "requests": 0}
        
        costs[today]["models"][model]["cost"] += cost
        costs[today]["models"][model]["tokens"] += tokens
        costs[today]["models"][model]["requests"] += 1
        
        # Save costs
        self._save_costs(costs)
        
        # Check alerts
        self._check_alerts(costs[today]["total_cost"])
        
        return {
            "daily_cost": costs[today]["total_cost"],
            "daily_limit": self.daily_limit,
            "remaining_budget": max(0, self.daily_limit - costs[today]["total_cost"]),
            "percentage_used": (costs[today]["total_cost"] / self.daily_limit) * 100
        }
    
    def _load_costs(self) -> Dict[str, Any]:
        """Load cost tracking data."""
        if self.cost_file.exists():
            try:
                with open(self.cost_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load cost data: {e}")
                # Return empty dict to continue with fresh cost tracking
        return {}
    
    def _save_costs(self, costs: Dict[str, Any]):
        """Save cost tracking data."""
        with open(self.cost_file, 'w') as f:
            json.dump(costs, f, indent=2)
    
    def _check_alerts(self, daily_cost: float):
        """Check if cost alerts should be sent."""
        percentage_used = (daily_cost / self.daily_limit) * 100
        
        for threshold in self.alert_thresholds:
            threshold_percentage = threshold * 100
            
            if (percentage_used >= threshold_percentage and 
                threshold_percentage not in self.alerts_sent):
                
                self._send_alert(threshold_percentage, daily_cost)
                self.alerts_sent.add(threshold_percentage)
    
    def _send_alert(self, threshold_percentage: float, current_cost: float):
        """Send cost alert with comprehensive alerting system."""
        alert_message = f"{threshold_percentage}% of daily budget used (${current_cost:.2f}/${self.daily_limit:.2f})"

        # Determine alert type based on threshold
        if threshold_percentage >= 95:
            alert_type = "critical"
        elif threshold_percentage >= 80:
            alert_type = "warning"
        else:
            alert_type = "info"

        # Log the alert
        if alert_type == "critical":
            self.logger.critical(f"Cost Alert: {alert_message}")
        elif alert_type == "warning":
            self.logger.warning(f"Cost Alert: {alert_message}")
        else:
            self.logger.info(f"Cost Alert: {alert_message}")

        # Store alert in history
        alert_record = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'threshold': threshold_percentage,
            'current_cost': current_cost,
            'daily_limit': self.daily_limit,
            'message': alert_message
        }

        # Add to alert history (keep last 100 alerts)
        if not hasattr(self, 'alert_history'):
            self.alert_history = []

        self.alert_history.append(alert_record)
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]

        # Console output with appropriate formatting
        if alert_type == "critical":
            print(f"🚨 CRITICAL COST ALERT: {alert_message}")
            print("⚠️ IMMEDIATE ACTION REQUIRED: Consider stopping processing!")
        elif alert_type == "warning":
            print(f"⚠️ COST WARNING: {alert_message}")
            print("💡 Consider monitoring usage more closely")
        else:
            print(f"ℹ️ COST INFO: {alert_message}")

        # Optional: Could integrate with external systems
        # - Email notifications
        # - Slack/Discord webhooks
        # - SMS alerts
        # - Dashboard updates
    
    def get_cost_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate cost report for specified days."""
        costs = self._load_costs()
        
        # Get last N days
        end_date = datetime.now()
        dates = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
        
        report = {
            "period": f"Last {days} days",
            "daily_costs": {},
            "total_cost": 0.0,
            "total_tokens": 0,
            "total_requests": 0,
            "average_daily_cost": 0.0,
            "model_breakdown": defaultdict(lambda: {"cost": 0.0, "tokens": 0, "requests": 0})
        }
        
        for date in dates:
            if date in costs:
                day_data = costs[date]
                report["daily_costs"][date] = day_data
                report["total_cost"] += day_data["total_cost"]
                report["total_tokens"] += day_data["total_tokens"]
                report["total_requests"] += day_data["requests"]
                
                # Aggregate model data
                for model, model_data in day_data.get("models", {}).items():
                    report["model_breakdown"][model]["cost"] += model_data["cost"]
                    report["model_breakdown"][model]["tokens"] += model_data["tokens"]
                    report["model_breakdown"][model]["requests"] += model_data["requests"]
        
        report["average_daily_cost"] = report["total_cost"] / days
        report["model_breakdown"] = dict(report["model_breakdown"])
        
        return report


class CostOptimizer:
    """Main cost optimization coordinator."""
    
    def __init__(self, daily_limit: float = 10.0):
        self.cache = IntelligentCache()
        self.batch_processor = BatchProcessor()
        self.cost_monitor = CostMonitor(daily_limit)
        self.optimization_history = []
    
    def analyze_usage_patterns(self) -> List[OptimizationRecommendation]:
        """Analyze usage and provide optimization recommendations."""
        recommendations = []
        
        # Get cache analytics
        cache_analytics = self.cache.get_cache_analytics()
        cache_hit_rate = cache_analytics["current_session"]["hit_rate"]
        
        # Get cost report
        cost_report = self.cost_monitor.get_cost_report(7)
        
        # Cache optimization recommendations
        if cache_hit_rate < 0.3:
            recommendations.append(OptimizationRecommendation(
                type="cache_optimization",
                description="Low cache hit rate. Consider increasing cache duration or improving prompt normalization.",
                potential_savings=cost_report["total_cost"] * 0.3,
                implementation_effort="low",
                priority="high"
            ))
        
        # Model optimization recommendations
        model_costs = cost_report["model_breakdown"]
        expensive_models = [model for model, data in model_costs.items() 
                          if data["cost"] > cost_report["total_cost"] * 0.5]
        
        if expensive_models:
            recommendations.append(OptimizationRecommendation(
                type="model_optimization",
                description=f"Consider using cheaper models for simple tasks. {expensive_models[0]} accounts for >50% of costs.",
                potential_savings=cost_report["total_cost"] * 0.4,
                implementation_effort="medium",
                priority="high"
            ))
        
        # Batching recommendations
        avg_requests_per_day = cost_report["total_requests"] / 7
        if avg_requests_per_day > 100:
            recommendations.append(OptimizationRecommendation(
                type="batching_optimization",
                description="High request volume. Implement request batching to reduce overhead.",
                potential_savings=cost_report["total_cost"] * 0.15,
                implementation_effort="medium",
                priority="medium"
            ))
        
        # Quality vs cost recommendations
        if cost_report["average_daily_cost"] > self.cost_monitor.daily_limit * 0.8:
            recommendations.append(OptimizationRecommendation(
                type="quality_tradeoff",
                description="Approaching daily limit. Consider reducing AI usage for low-priority tasks.",
                potential_savings=cost_report["total_cost"] * 0.25,
                implementation_effort="low",
                priority="high"
            ))
        
        return recommendations
    
    def implement_optimization(self, recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """Implement an optimization recommendation."""
        result = {
            "recommendation": recommendation.type,
            "implemented": False,
            "details": ""
        }
        
        if recommendation.type == "cache_optimization":
            # Optimize cache settings
            optimization_result = self.cache.optimize_cache()
            result["implemented"] = True
            result["details"] = f"Removed {optimization_result['expired_removed']} expired entries"
        
        elif recommendation.type == "model_optimization":
            # This would require configuration changes
            result["details"] = "Requires manual configuration update to use cheaper models"
        
        elif recommendation.type == "batching_optimization":
            # Adjust batch settings
            self.batch_processor.batch_size = min(10, self.batch_processor.batch_size + 2)
            result["implemented"] = True
            result["details"] = f"Increased batch size to {self.batch_processor.batch_size}"
        
        self.optimization_history.append({
            "timestamp": datetime.now().isoformat(),
            "recommendation": recommendation.type,
            "implemented": result["implemented"]
        })
        
        return result
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""
        recommendations = self.analyze_usage_patterns()
        cache_analytics = self.cache.get_cache_analytics()
        cost_report = self.cost_monitor.get_cost_report(7)
        
        return {
            "cost_summary": cost_report,
            "cache_performance": cache_analytics,
            "recommendations": [
                {
                    "type": rec.type,
                    "description": rec.description,
                    "potential_savings": rec.potential_savings,
                    "priority": rec.priority
                }
                for rec in recommendations
            ],
            "optimization_history": self.optimization_history[-10:],  # Last 10 optimizations
            "overall_efficiency": {
                "cache_hit_rate": cache_analytics["current_session"]["hit_rate"],
                "cost_per_request": cost_report["total_cost"] / max(1, cost_report["total_requests"]),
                "daily_budget_utilization": cost_report["average_daily_cost"] / self.cost_monitor.daily_limit
            }
        }
