"""Summarizer Module

This module handles generating English summaries using Google Gemini API.
"""

import google.generativeai as genai
from typing import List, Optional
import time
from langdetect import detect, LangDetectException
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


class RateLimiter:
    """Manages API rate limiting for RPM and daily quotas."""
    
    def __init__(self, max_rpm: int = 3, max_daily: int = 15, 
                 data_dir: str = None, logger=None):
        """Initialize rate limiter.
        
        Args:
            max_rpm: Maximum requests per minute.
            max_daily: Maximum requests per day.
            data_dir: Directory to store quota file.
            logger: Logger instance.
        """
        self.max_rpm = max_rpm
        self.max_daily = max_daily
        self.logger = logger
        
        # Track request times for RPM calculation
        self.request_times = []
        
        # Setup quota file
        if data_dir:
            self.quota_file = Path(data_dir) / "api_quota.json"
        else:
            self.quota_file = Path("data") / "api_quota.json"
        
        # Load or initialize daily count
        self._load_quota()
    
    def _load_quota(self):
        """Load quota data from file."""
        try:
            if self.quota_file.exists():
                with open(self.quota_file, 'r') as f:
                    data = json.load(f)
                    
                # Check if it's a new day
                last_date = data.get('date', '')
                today = datetime.now().strftime('%Y-%m-%d')
                
                if last_date == today:
                    self.daily_count = data.get('count', 0)
                else:
                    # New day, reset counter
                    self.daily_count = 0
                    self._save_quota()
            else:
                self.daily_count = 0
                self._save_quota()
                
            if self.logger:
                self.logger.info(f"API quota loaded: {self.daily_count}/{self.max_daily} requests used today")
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to load quota file: {e}, starting fresh")
            self.daily_count = 0
    
    def _save_quota(self):
        """Save quota data to file."""
        try:
            # Ensure directory exists
            self.quota_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'count': self.daily_count
            }
            
            with open(self.quota_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save quota file: {e}")
    
    def can_make_request(self) -> bool:
        """Check if we can make a request without exceeding limits.
        
        Returns:
            True if request is allowed, False otherwise.
        """
        # Check daily limit
        if self.daily_count >= self.max_daily:
            if self.logger:
                self.logger.warning(f"Daily API limit reached: {self.daily_count}/{self.max_daily}")
            return False
        
        # Check RPM limit
        now = time.time()
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.max_rpm:
            if self.logger:
                self.logger.debug(f"RPM limit reached: {len(self.request_times)}/{self.max_rpm}")
            return False
        
        return True
    
    def wait_if_needed(self):
        """Wait if necessary to comply with rate limits."""
        while not self.can_make_request():
            # If daily limit reached, don't wait
            if self.daily_count >= self.max_daily:
                return
            
            # Calculate wait time for RPM
            now = time.time()
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            if len(self.request_times) >= self.max_rpm:
                # Wait until oldest request is 60 seconds old
                oldest = min(self.request_times)
                wait_time = 60 - (now - oldest) + 1  # +1 for safety margin
                
                if self.logger:
                    self.logger.info(f"Rate limit: waiting {wait_time:.1f}s (RPM: {len(self.request_times)}/{self.max_rpm})")
                
                time.sleep(wait_time)
    
    def record_request(self):
        """Record a successful API request."""
        now = time.time()
        self.request_times.append(now)
        self.daily_count += 1
        self._save_quota()
        
        if self.logger:
            self.logger.debug(f"API request recorded: {self.daily_count}/{self.max_daily} daily, {len(self.request_times)}/{self.max_rpm} per minute")
    
    def get_daily_count(self) -> int:
        """Get current daily request count.
        
        Returns:
            Number of requests made today.
        """
        return self.daily_count
    
    def get_remaining_quota(self) -> int:
        """Get remaining daily quota.
        
        Returns:
            Number of requests remaining today.
        """
        return max(0, self.max_daily - self.daily_count)


class Summarizer:
    """Generates English summaries for articles using Google Gemini."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-pro",
                 min_length: int = 100, max_length: int = 300,
                 max_retries: int = 3, max_rpm: int = 3, 
                 max_daily_requests: int = 15, data_dir: str = None,
                 logger=None):
        """Initialize summarizer.
        
        Args:
            api_key: Google Gemini API key.
            model_name: Model name to use.
            min_length: Minimum summary length in words.
            max_length: Maximum summary length in words.
            max_retries: Maximum retry attempts for API calls.
            max_rpm: Maximum requests per minute.
            max_daily_requests: Maximum requests per day.
            data_dir: Directory for storing quota data.
            logger: Logger instance.
        """
        self.api_key = api_key
        self.model_name = model_name
        self.min_length = min_length
        self.max_length = max_length
        self.max_retries = max_retries
        self.logger = logger
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_rpm=max_rpm,
            max_daily=max_daily_requests,
            data_dir=data_dir,
            logger=logger
        )
        
        # Configure Gemini
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            self.enabled = True
            
            if self.logger:
                self.logger.info(f"Gemini API initialized with model: {model_name}")
                self.logger.info(f"Rate limits: {max_rpm} RPM, {max_daily_requests} requests/day")
        else:
            self.enabled = False
            if self.logger:
                self.logger.warning("Gemini API key not provided, summarization disabled")
    
    def summarize_articles(self, articles: List) -> List:
        """Generate summaries for multiple articles.
        
        Args:
            articles: List of Article objects.
        
        Returns:
            List of Article objects with summaries filled.
        """
        if not self.enabled:
            if self.logger:
                self.logger.warning("Summarization disabled, using fallback summaries")
            return [self._create_fallback_summary(article) for article in articles]
        
        # Check daily quota before starting
        remaining = self.rate_limiter.get_remaining_quota()
        if remaining <= 0:
            if self.logger:
                self.logger.warning(f"Daily API quota exhausted ({self.rate_limiter.get_daily_count()}/{self.rate_limiter.max_daily}), using fallback summaries")
            return [self._create_fallback_summary(article) for article in articles]
        
        if self.logger:
            self.logger.info(f"Generating summaries for {len(articles)} articles (Quota: {remaining} requests remaining)")
        
        results = []
        processed_count = 0
        
        for i, article in enumerate(articles):
            # Check if we still have quota
            if not self.rate_limiter.can_make_request():
                if self.logger:
                    self.logger.warning(f"API quota limit reached after {processed_count} articles, using fallback for remaining")
                # Use fallback for remaining articles
                article.summary = self._create_fallback_summary(article).summary
                article.title_zh = ""
                article.summary_zh = ""
                results.append(article)
                continue
            
            try:
                if self.logger:
                    self.logger.debug(f"Processing article {i+1}/{len(articles)}: {article.title}")
                
                # Generate English summary
                summary = self._generate_summary(article)
                article.summary = summary
                
                # Translate title to Chinese
                article.title_zh = self._translate_to_chinese(article.title, "title")
                
                # Translate summary to Chinese
                article.summary_zh = self._translate_to_chinese(summary, "summary")
                
                results.append(article)
                processed_count += 1
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error generating summary for {article.title}: {e}")
                article.summary = self._create_fallback_summary(article).summary
                article.title_zh = ""
                article.summary_zh = ""
                results.append(article)
        
        if self.logger:
            success_count = sum(1 for a in results if a.summary and len(a.summary) > 50)
            self.logger.info(f"Successfully generated {success_count}/{len(articles)} summaries")
            self.logger.info(f"API usage today: {self.rate_limiter.get_daily_count()}/{self.rate_limiter.max_daily}")
        
        return results
    
    def _generate_summary(self, article) -> str:
        """Generate summary for a single article.
        
        Args:
            article: Article object.
        
        Returns:
            English summary string.
        """
        # Get content to summarize
        content = article.content or article.description or article.title
        
        if not content or len(content) < 50:
            return self._create_fallback_text(article)
        
        # Detect language
        language = self._detect_language(content)
        
        if self.logger:
            self.logger.debug(f"Detected language: {language}")
        
        # Generate summary with retry
        for attempt in range(self.max_retries):
            try:
                if language and language != 'en':
                    # Non-English content: translate and summarize
                    summary = self._translate_and_summarize(content, language)
                else:
                    # English content: just summarize
                    summary = self._summarize_english(content)
                
                if summary and len(summary.split()) >= self.min_length // 2:
                    return summary
                
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Summary generation attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    if self.logger:
                        self.logger.error(f"All retry attempts failed for article: {article.title}")
        
        # Fallback
        return self._create_fallback_text(article)
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of text.
        
        Args:
            text: Text to analyze.
        
        Returns:
            Language code or None.
        """
        try:
            # Use first 1000 characters for detection
            sample = text[:1000]
            lang = detect(sample)
            return lang
        except LangDetectException:
            return None
    
    def _translate_and_summarize(self, content: str, source_lang: str) -> str:
        """Translate non-English content and generate summary.
        
        Args:
            content: Article content.
            source_lang: Source language code.
        
        Returns:
            English summary.
        """
        # Wait if needed to comply with rate limits
        self.rate_limiter.wait_if_needed()
        
        # Check if we can still make request
        if not self.rate_limiter.can_make_request():
            raise Exception("API quota limit reached")
        
        # Truncate content if too long (Gemini has token limits)
        max_chars = 10000
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        
        prompt = f"""Please read the following article in {source_lang} and provide a concise English summary.

Requirements:
- Summary should be in English
- Length: {self.min_length}-{self.max_length} words
- Focus on key points and main ideas
- Use clear and professional language

Article:
{content}

English Summary:"""
        
        response = self.model.generate_content(prompt)
        summary = response.text.strip()
        
        # Record successful request
        self.rate_limiter.record_request()
        
        return summary
    
    def _summarize_english(self, content: str) -> str:
        """Generate summary for English content.
        
        Args:
            content: Article content in English.
        
        Returns:
            English summary.
        """
        # Wait if needed to comply with rate limits
        self.rate_limiter.wait_if_needed()
        
        # Check if we can still make request
        if not self.rate_limiter.can_make_request():
            raise Exception("API quota limit reached")
        
        # Truncate content if too long
        max_chars = 10000
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        
        prompt = f"""Please provide a concise summary of the following article.

Requirements:
- Length: {self.min_length}-{self.max_length} words
- Focus on key points and main ideas
- Use clear and professional language

Article:
{content}

Summary:"""
        
        response = self.model.generate_content(prompt)
        summary = response.text.strip()
        
        # Record successful request
        self.rate_limiter.record_request()
        
        return summary
    
    def _create_fallback_summary(self, article) -> 'Article':
        """Create fallback summary when AI generation fails.
        
        Args:
            article: Article object.
        
        Returns:
            Article with fallback summary.
        """
        article.summary = self._create_fallback_text(article)
        return article
    
    def _create_fallback_text(self, article) -> str:
        """Create fallback summary text.
        
        Args:
            article: Article object.
        
        Returns:
            Fallback summary string.
        """
        # Use description if available
        if article.description and len(article.description) > 50:
            # Truncate to reasonable length
            desc = article.description[:500]
            if len(article.description) > 500:
                desc += "..."
            return f"{article.title}\n\n{desc}"
        
        # Otherwise just use title
        return article.title
    
    def _translate_to_chinese(self, text: str, content_type: str = "text") -> str:
        """Translate English text to Chinese.
        
        Args:
            text: Text to translate.
            content_type: Type of content (title, summary, text).
        
        Returns:
            Chinese translation.
        """
        if not text or len(text.strip()) == 0:
            return ""
        
        try:
            # Wait if needed to comply with rate limits
            self.rate_limiter.wait_if_needed()
            
            # Check if we can still make request
            if not self.rate_limiter.can_make_request():
                if self.logger:
                    self.logger.warning(f"API quota limit reached, skipping {content_type} translation")
                return ""
            
            if content_type == "title":
                prompt = f"""Please translate the following English title to Chinese. Only provide the translation, no explanations.

English Title:
{text}

Chinese Translation:"""
            else:
                prompt = f"""Please translate the following English text to Chinese. Maintain the same tone and style. Only provide the translation, no explanations.

English Text:
{text}

Chinese Translation:"""
            
            response = self.model.generate_content(prompt)
            translation = response.text.strip()
            
            # Record successful request
            self.rate_limiter.record_request()
            
            if self.logger:
                self.logger.debug(f"Translated {content_type} to Chinese: {translation[:50]}...")
            
            return translation
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Translation failed for {content_type}: {e}")
            return ""  # Return empty string on failure
    
    def test_connection(self) -> bool:
        """Test Gemini API connection.
        
        Returns:
            True if connection successful, False otherwise.
        """
        if not self.enabled:
            return False
        
        try:
            response = self.model.generate_content("Hello, this is a test.")
            return bool(response.text)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Gemini API connection test failed: {e}")
            return False
