#!/usr/bin/env python3
"""
OpenAI API integration for enhanced text formatting and classification.
Provides AI-powered improvements to text processing with cost optimization.
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import sqlite3
from pathlib import Path
from types import SimpleNamespace

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI integration."""

    provider: str = "openai"
    api_key: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    base_url: Optional[str] = None
    app_name: Optional[str] = "AI Data Pipeline"
    app_url: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.3
    enable_caching: bool = True
    cache_duration_hours: int = 24
    max_requests_per_minute: int = 60
    enable_content_enhancement: bool = False
    enable_ai_classification: bool = True
    cost_limit_per_day: float = 10.0  # USD


class TokenCounter:
    """Utility for counting tokens and estimating costs."""

    # Approximate token costs (as of 2024)
    TOKEN_COSTS = {
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},  # per 1K tokens
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    }

    @staticmethod
    def estimate_tokens(text) -> int:
        """Rough estimation of token count (1 token ≈ 4 characters)."""
        if isinstance(text, str):
            return len(text) // 4
        elif isinstance(text, int):
            return text // 4  # Assume it's character count
        else:
            return 0

    @classmethod
    def estimate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate API call cost in USD."""
        if model not in cls.TOKEN_COSTS:
            model = "gpt-3.5-turbo"  # Default fallback

        costs = cls.TOKEN_COSTS[model]
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]

        return input_cost + output_cost


class ResponseCache:
    """SQLite-based cache for OpenAI responses."""

    def __init__(self, cache_file: str = "openai_cache.db"):
        self.cache_file = Path(cache_file)
        self.init_cache()

    def init_cache(self):
        """Initialize the cache database."""
        with sqlite3.connect(self.cache_file) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS openai_cache (
                    request_hash TEXT PRIMARY KEY,
                    prompt_hash TEXT,
                    model TEXT,
                    response TEXT,
                    tokens_used INTEGER,
                    cost REAL,
                    timestamp TEXT,
                    expires_at TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON openai_cache(expires_at)
            """)

    def get_cache_key(self, prompt: str, model: str, **kwargs) -> str:
        """Generate cache key for request."""
        cache_data = {"prompt": prompt, "model": model, **kwargs}
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()

    def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired."""
        with sqlite3.connect(self.cache_file) as conn:
            conn.row_factory = sqlite3.Row

            row = conn.execute(
                """
                SELECT * FROM openai_cache 
                WHERE request_hash = ? AND expires_at > ?
            """,
                (cache_key, datetime.now().isoformat()),
            ).fetchone()

            if row:
                return {
                    "response": row["response"],
                    "tokens_used": row["tokens_used"],
                    "cost": row["cost"],
                    "cached": True,
                }

        return None

    def cache_response(
        self,
        cache_key: str,
        prompt: str,
        model: str,
        response: str,
        tokens_used: int,
        cost: float,
        cache_duration_hours: int = 24,
    ):
        """Cache API response."""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        expires_at = datetime.now() + timedelta(hours=cache_duration_hours)

        with sqlite3.connect(self.cache_file) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO openai_cache 
                (request_hash, prompt_hash, model, response, tokens_used, cost, timestamp, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    cache_key,
                    prompt_hash,
                    model,
                    response,
                    tokens_used,
                    cost,
                    datetime.now().isoformat(),
                    expires_at.isoformat(),
                ),
            )

    def cleanup_expired(self):
        """Remove expired cache entries."""
        with sqlite3.connect(self.cache_file) as conn:
            result = conn.execute(
                """
                DELETE FROM openai_cache WHERE expires_at < ?
            """,
                (datetime.now().isoformat(),),
            )

            return result.rowcount


class RateLimiter:
    """Rate limiting for OpenAI API calls."""

    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.requests = []

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()

        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]

        # Check if we need to wait
        if len(self.requests) >= self.max_requests:
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                logging.info(f"Rate limit reached, waiting {sleep_time:.1f} seconds")
                time.sleep(sleep_time)

        # Record this request
        self.requests.append(now)


class CostTracker:
    """Track daily API costs."""

    def __init__(self, cost_file: str = "openai_costs.json"):
        self.cost_file = Path(cost_file)
        self.logger = logging.getLogger(f"{__name__}.CostTracker")
        self.costs = self.load_costs()

    def load_costs(self) -> Dict[str, float]:
        """Load cost tracking data."""
        if self.cost_file.exists():
            try:
                with open(self.cost_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cost data: {e}")
                # Continue with empty cost data - not critical for operation
        return {}

    def save_costs(self):
        """Save cost tracking data."""
        with open(self.cost_file, "w") as f:
            json.dump(self.costs, f, indent=2)

    def add_cost(self, cost: float):
        """Add cost for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        self.costs[today] = self.costs.get(today, 0.0) + cost
        self.save_costs()

    def get_daily_cost(self, date: str = None) -> float:
        """Get cost for specific date (default: today)."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.costs.get(date, 0.0)

    def check_daily_limit(self, limit: float) -> bool:
        """Check if daily cost limit would be exceeded."""
        return self.get_daily_cost() < limit


class OpenAIClient:
    """Enhanced OpenAI client with caching, rate limiting, and cost tracking."""

    def __init__(self, config: OpenAIConfig):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not installed. Run: pip install openai")

        self.config = config
        self.client = None
        self.provider = (config.provider or "openai").lower()

        if self.provider not in {"openai", "openrouter", "lmstudio", "ollama"}:
            raise ValueError(f"Unsupported provider: {self.provider}")

        # Set up provider credentials
        resolved_key = None
        if config.api_key:
            resolved_key = config.api_key
        elif self.provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
            resolved_key = os.getenv("OPENROUTER_API_KEY")
        elif os.getenv("OPENAI_API_KEY"):
            resolved_key = os.getenv("OPENAI_API_KEY")
        elif self.provider in {"lmstudio", "ollama"}:
            # OpenAI-compatible local providers typically do not require auth
            resolved_key = "local-provider"
        else:
            key_name = (
                "OPENROUTER_API_KEY"
                if self.provider == "openrouter"
                else "OPENAI_API_KEY"
            )
            raise ValueError(
                f"API key not provided. Set {key_name} environment variable or pass api_key in config."
            )

        if self.provider in {"openai", "openrouter"} and resolved_key:
            lowered = resolved_key.upper()
            if (
                resolved_key.strip().startswith("<")
                or "YOUR_" in lowered
                or "SET_" in lowered
                or "PLACEHOLDER" in lowered
            ):
                raise ValueError(
                    f"Provider {self.provider} requires a real API key (placeholder detected)."
                )

        base_url = config.base_url
        if self.provider == "openrouter":
            base_url = base_url or os.getenv(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            )
        elif self.provider == "lmstudio":
            base_url = base_url or os.getenv(
                "LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1"
            )
        elif self.provider == "ollama":
            base_url = base_url or os.getenv(
                "OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"
            )

        default_headers = None
        if self.provider == "openrouter":
            site_url = config.app_url or os.getenv("OPENROUTER_SITE_URL")
            app_name = config.app_name or os.getenv(
                "OPENROUTER_APP_NAME", "AI Data Pipeline"
            )
            default_headers = {"X-Title": app_name}
            if site_url:
                default_headers["HTTP-Referer"] = site_url

        # Support modern SDK (OpenAI client class) and legacy module API
        try:
            if hasattr(openai, "OpenAI"):
                client_kwargs = {"api_key": resolved_key}
                if base_url:
                    client_kwargs["base_url"] = base_url
                if default_headers:
                    client_kwargs["default_headers"] = default_headers
                self.client = openai.OpenAI(**client_kwargs)
            else:
                openai.api_key = resolved_key
                if base_url:
                    openai.api_base = base_url
        except Exception:
            openai.api_key = resolved_key
            if base_url:
                openai.api_base = base_url
            self.client = None

        # Initialize components
        self.cache = ResponseCache() if config.enable_caching else None
        self.rate_limiter = RateLimiter(config.max_requests_per_minute)
        self.cost_tracker = CostTracker()

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def make_request(
        self, prompt: str, system_prompt: str = None, **kwargs
    ) -> Dict[str, Any]:
        """Make OpenAI API request with caching and rate limiting."""
        # Check daily cost limit
        if not self.cost_tracker.check_daily_limit(self.config.cost_limit_per_day):
            raise Exception(
                f"Daily cost limit of ${self.config.cost_limit_per_day} reached"
            )

        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Check cache
        cache_key = None
        if self.cache:
            cache_key = self.cache.get_cache_key(
                prompt=prompt,
                model=self.config.model,
                system_prompt=system_prompt,
                **kwargs,
            )
            cached_response = self.cache.get_cached_response(cache_key)
            if cached_response:
                self.logger.info("Using cached response")
                return cached_response

        # Rate limiting
        self.rate_limiter.wait_if_needed()

        # Estimate cost
        input_tokens = TokenCounter.estimate_tokens(prompt + (system_prompt or ""))
        estimated_cost = TokenCounter.estimate_cost(
            self.config.model, input_tokens, self.config.max_tokens
        )

        try:
            # Make API call
            if self.client is not None:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    **kwargs,
                )
            else:
                response = openai.ChatCompletion.create(
                    model=self.config.model,
                    messages=messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    **kwargs,
                )

            # Extract response data
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            if usage is None:
                usage = SimpleNamespace(
                    prompt_tokens=0, completion_tokens=0, total_tokens=0
                )

            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0
            tokens_used = getattr(usage, "total_tokens", 0) or (
                prompt_tokens + completion_tokens
            )
            actual_cost = TokenCounter.estimate_cost(
                self.config.model, prompt_tokens, completion_tokens
            )

            # Track cost
            self.cost_tracker.add_cost(actual_cost)

            # Cache response
            if self.cache and cache_key:
                self.cache.cache_response(
                    cache_key,
                    prompt,
                    self.config.model,
                    content,
                    tokens_used,
                    actual_cost,
                    self.config.cache_duration_hours,
                )

            self.logger.info(
                f"API call successful ({self.provider}). Tokens: {tokens_used}, Cost: ${actual_cost:.4f}"
            )

            return {
                "response": content,
                "tokens_used": tokens_used,
                "cost": actual_cost,
                "cached": False,
                "provider": self.provider,
            }

        except Exception as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise

    def classify_text(self, text: str) -> Dict[str, Any]:
        """Use AI to classify text as question or answer."""
        system_prompt = """You are a text classifier. Analyze the given text and determine if it's primarily a question or an answer/statement.

Respond with a JSON object containing:
- "classification": "question" or "answer"
- "confidence": float between 0.0 and 1.0
- "reasoning": brief explanation

Consider:
- Questions often end with "?" or start with question words (what, how, why, etc.)
- Answers provide information, explanations, or statements
- Some text might be mixed - classify based on the primary intent"""

        try:
            result = self.make_request(text, system_prompt)

            # Parse JSON response
            response_data = json.loads(result["response"])

            return {
                "classification": response_data.get("classification", "answer"),
                "confidence": response_data.get("confidence", 0.5),
                "reasoning": response_data.get("reasoning", ""),
                "tokens_used": result["tokens_used"],
                "cost": result["cost"],
                "cached": result["cached"],
            }

        except json.JSONDecodeError:
            # Fallback to simple text analysis
            classification = "question" if "?" in text else "answer"
            return {
                "classification": classification,
                "confidence": 0.3,
                "reasoning": "Fallback classification due to parsing error",
                "tokens_used": result.get("tokens_used", 0),
                "cost": result.get("cost", 0),
                "cached": False,
            }
        except Exception as e:
            self.logger.error(f"AI classification failed: {str(e)}")
            # Return default classification
            return {
                "classification": "answer",
                "confidence": 0.1,
                "reasoning": f"Error: {str(e)}",
                "tokens_used": 0,
                "cost": 0,
                "cached": False,
            }

    def enhance_content(
        self, text: str, enhancement_type: str = "clarity"
    ) -> Dict[str, Any]:
        """Use AI to enhance content quality."""
        enhancement_prompts = {
            "clarity": "Improve the clarity and readability of this text while preserving its meaning and structure. Fix any grammar issues and make it more concise if possible.",
            "grammar": "Fix any grammar, spelling, and punctuation errors in this text while preserving its original meaning and style.",
            "structure": "Improve the structure and organization of this text to make it more logical and easier to follow.",
            "completeness": "If this text appears incomplete or could benefit from additional context, suggest improvements while maintaining accuracy.",
        }

        system_prompt = f"""You are a text editor. {enhancement_prompts.get(enhancement_type, enhancement_prompts["clarity"])}

Return only the improved text without any additional commentary or explanations."""

        try:
            result = self.make_request(text, system_prompt)

            return {
                "enhanced_text": result["response"].strip(),
                "original_length": len(text),
                "enhanced_length": len(result["response"]),
                "tokens_used": result["tokens_used"],
                "cost": result["cost"],
                "cached": result["cached"],
            }

        except Exception as e:
            self.logger.error(f"Content enhancement failed: {str(e)}")
            return {
                "enhanced_text": text,  # Return original on error
                "original_length": len(text),
                "enhanced_length": len(text),
                "tokens_used": 0,
                "cost": 0,
                "cached": False,
                "error": str(e),
            }

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        today_cost = self.cost_tracker.get_daily_cost()

        stats = {
            "daily_cost": today_cost,
            "daily_limit": self.config.cost_limit_per_day,
            "remaining_budget": max(0, self.config.cost_limit_per_day - today_cost),
            "cache_enabled": self.config.enable_caching,
            "model": self.config.model,
        }

        if self.cache:
            # Get cache statistics
            with sqlite3.connect(self.cache.cache_file) as conn:
                cache_stats = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_entries,
                        SUM(cost) as total_cached_cost,
                        COUNT(CASE WHEN expires_at > ? THEN 1 END) as active_entries
                    FROM openai_cache
                """,
                    (datetime.now().isoformat(),),
                ).fetchone()

                stats.update(
                    {
                        "cache_entries": cache_stats[0],
                        "cache_cost_saved": cache_stats[1] or 0,
                        "active_cache_entries": cache_stats[2],
                    }
                )

        return stats

    def cleanup_cache(self) -> int:
        """Clean up expired cache entries."""
        if self.cache:
            return self.cache.cleanup_expired()
        return 0
