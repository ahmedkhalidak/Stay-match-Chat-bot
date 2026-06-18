"""
Gemini FAQ Service with caching, rate limiting, and enhanced logging.
Uses Gemini 2.5 Flash Lite for FAQ answering as a fallback to KnowledgeService.
"""

import time
import hashlib
from datetime import datetime, date
from typing import Optional, Dict, Any
from google.generativeai import GenerativeModel, configure
from app.core.config import settings
from app.prompts.faq_prompt import get_faq_prompt
from app.utils.logger import debug_log
from app.utils.language_detector import detect_language


class GeminiFaqService:
    """Gemini-based FAQ service with caching and rate limiting."""

    def __init__(self):
        self.enabled = settings.enable_gemini_faq
        self.api_key = settings.gemini_api_key
        self.daily_limit = settings.gemini_daily_limit
        self.cache_ttl = settings.gemini_cache_ttl_seconds
        self.max_tokens = settings.gemini_max_tokens
        self.timeout = settings.gemini_timeout_seconds

        # Rate limiting
        self.daily_calls = 0
        self.last_reset_date = date.today()

        # In-memory cache: {normalized_question: (answer, timestamp)}
        self.cache: Dict[str, tuple[str, float]] = {}

        # Lazy initialization of Gemini client
        self._model: Optional[GenerativeModel] = None

    def _init_model(self):
        """Lazy initialize Gemini model."""
        if not self.api_key:
            debug_log("GEMINI_INIT", "No API key provided")
            return

        try:
            configure(api_key=self.api_key)
            self._model = GenerativeModel("gemini-2.5-flash-lite")
            debug_log("GEMINI_INIT", "Model initialized successfully")
        except Exception as e:
            debug_log("GEMINI_INIT_ERROR", f"Failed to initialize: {e}")

    def _reset_daily_limit(self):
        """Reset daily call counter at midnight."""
        today = date.today()
        if today != self.last_reset_date:
            self.daily_calls = 0
            self.last_reset_date = today
            debug_log("GEMINI_RATE_LIMIT", "Daily counter reset")

    def _check_rate_limit(self) -> bool:
        """Check if daily rate limit is exceeded."""
        self._reset_daily_limit()

        if self.daily_calls >= self.daily_limit:
            debug_log("GEMINI_RATE_LIMIT", f"Limit exceeded: {self.daily_calls}/{self.daily_limit}")
            return False

        # Log warning at 80% and 90%
        if self.daily_calls >= int(self.daily_limit * 0.9):
            debug_log("GEMINI_RATE_LIMIT", f"Warning: 90% of limit reached ({self.daily_calls}/{self.daily_limit})")
        elif self.daily_calls >= int(self.daily_limit * 0.8):
            debug_log("GEMINI_RATE_LIMIT", f"Warning: 80% of limit reached ({self.daily_calls}/{self.daily_limit})")

        return True

    def _normalize_question(self, question: str) -> str:
        """Normalize question for cache key."""
        return hashlib.md5(question.lower().strip().encode()).hexdigest()

    def _get_from_cache(self, normalized_question: str) -> Optional[str]:
        """Get answer from cache if not expired."""
        if normalized_question in self.cache:
            answer, timestamp = self.cache[normalized_question]
            if time.time() - timestamp < self.cache_ttl:
                debug_log("GEMINI_CACHE_HIT", normalized_question[:16])
                return answer
            else:
                # Remove expired entry
                del self.cache[normalized_question]
                debug_log("GEMINI_CACHE_EXPIRE", normalized_question[:16])
        return None

    def _set_cache(self, normalized_question: str, answer: str):
        """Store answer in cache."""
        self.cache[normalized_question] = (answer, time.time())
        debug_log("GEMINI_CACHE_SET", normalized_question[:16])

    def _cleanup_cache(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= self.cache_ttl
        ]
        for key in expired_keys:
            del self.cache[key]
        if expired_keys:
            debug_log("GEMINI_CACHE_CLEANUP", f"Removed {len(expired_keys)} expired entries")

    def _cleanup_cache_if_needed(self):
        """Clean up cache if it exceeds maximum size."""
        max_cache_size = 1000
        if len(self.cache) > max_cache_size:
            # Remove oldest 20% of entries
            sorted_entries = sorted(self.cache.items(), key=lambda x: x[1][1])
            to_remove = int(max_cache_size * 0.2)
            for key, _ in sorted_entries[:to_remove]:
                del self.cache[key]
            debug_log("GEMINI_CACHE_SIZE_LIMIT", f"Removed {to_remove} oldest entries")

    async def generate_answer(self, question: str) -> Optional[str]:
        """
        Generate FAQ answer using Gemini with caching and rate limiting.

        Args:
            question: User's question

        Returns:
            Generated answer or None if failed
        """
        if not self.enabled:
            debug_log("GEMINI_DISABLED", "Gemini FAQ is disabled")
            return None

        if not self.api_key:
            debug_log("GEMINI_NO_KEY", "No API key configured")
            return None

        # Initialize model if needed
        if not self._model:
            self._init_model()
            if not self._model:
                return None

        # Check rate limit
        if not self._check_rate_limit():
            return None

        # Check cache
        normalized_q = self._normalize_question(question)
        cached_answer = self._get_from_cache(normalized_q)
        if cached_answer:
            return cached_answer

        # Detect language
        lang = detect_language(question)
        debug_log("GEMINI_LANGUAGE", f"Detected: {lang}")

        # Get system prompt
        system_prompt = get_faq_prompt(lang)

        # Generate answer with retry logic
        answer = await self._generate_with_retry(question, system_prompt, lang)

        if answer:
            # Cache the answer
            self._set_cache(normalized_q, answer)
            self.daily_calls += 1
            debug_log("GEMINI_CALL_SUCCESS", f"Total calls today: {self.daily_calls}")

            # Clean up cache if needed
            self._cleanup_cache_if_needed()

        return answer

    async def _generate_with_retry(self, question: str, system_prompt: str, lang: str) -> Optional[str]:
        """Generate answer with exponential backoff retry."""
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                # Generate response
                response = self._model.generate_content(
                    f"{system_prompt}\n\nUser: {question}",
                    generation_config={
                        "max_output_tokens": self.max_tokens,
                        "temperature": 0.7,
                    }
                )

                duration = time.time() - start_time
                answer = response.text.strip()

                debug_log("GEMINI_GENERATE", f"Duration: {duration:.2f}s, Length: {len(answer)}")

                return answer

            except Exception as e:
                error_msg = str(e).lower()
                debug_log("GEMINI_ERROR", f"Attempt {attempt + 1}/{max_retries}: {e}")

                # Check if it's a rate limit error
                if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        debug_log("GEMINI_RETRY", f"Rate limited, retrying in {delay}s")
                        time.sleep(delay)
                        continue
                    else:
                        debug_log("GEMINI_RATE_LIMIT_EXCEEDED", "Max retries reached")
                        return None

                # For other errors, don't retry
                if attempt == 0:
                    return None

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        self._reset_daily_limit()
        return {
            "enabled": self.enabled,
            "daily_calls": self.daily_calls,
            "daily_limit": self.daily_limit,
            "cache_size": len(self.cache),
            "cache_ttl": self.cache_ttl,
        }
