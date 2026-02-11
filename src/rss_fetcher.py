"""RSS Fetcher Module

This module handles fetching and parsing RSS feeds.
"""

import requests
import feedparser
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import time
import pytz


@dataclass
class Article:
    """Article data model."""
    title: str
    link: str
    published: datetime
    description: str = ""
    source: str = ""
    source_url: str = ""
    content: str = ""
    summary: str = ""
    summary_zh: str = ""
    title_zh: str = ""
    
    def __repr__(self) -> str:
        return f"Article(title='{self.title[:50]}...', link='{self.link}')"


class RSSFetcher:
    """Fetches and parses RSS feeds."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, logger=None):
        """Initialize RSS fetcher.
        
        Args:
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
            logger: Logger instance.
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logger
        
        # Set up session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def fetch_articles(self, rss_sources: List, start_time: datetime, 
                      end_time: datetime) -> List[Article]:
        """Fetch articles from RSS sources within time range.
        
        Args:
            rss_sources: List of RSSSource objects.
            start_time: Start time for filtering articles.
            end_time: End time for filtering articles.
        
        Returns:
            List of Article objects.
        """
        all_articles = []
        
        if self.logger:
            self.logger.info(f"Fetching articles from {len(rss_sources)} RSS sources")
            self.logger.info(f"Time range: {start_time} to {end_time}")
        
        for source in rss_sources:
            try:
                articles = self._fetch_source(source, start_time, end_time)
                all_articles.extend(articles)
                
                if self.logger:
                    self.logger.info(f"Fetched {len(articles)} articles from {source.title}")
                
                # Small delay to avoid overwhelming servers
                time.sleep(0.5)
                
            except Exception as e:
                if self.logger:
                    self.logger.log_rss_source_error(source.xml_url, e)
                continue
        
        if self.logger:
            self.logger.info(f"Total articles fetched: {len(all_articles)}")
        
        return all_articles
    
    def _fetch_source(self, source, start_time: datetime, end_time: datetime) -> List[Article]:
        """Fetch articles from a single RSS source.
        
        Args:
            source: RSSSource object.
            start_time: Start time for filtering.
            end_time: End time for filtering.
        
        Returns:
            List of Article objects.
        """
        articles = []
        
        # Fetch RSS feed with retries
        feed_content = self._fetch_with_retry(source.xml_url)
        if not feed_content:
            return articles
        
        # Parse feed
        feed = feedparser.parse(feed_content)
        
        if feed.bozo:
            if self.logger:
                self.logger.warning(f"Feed parsing warning for {source.xml_url}: {feed.bozo_exception}")
        
        # Extract articles
        for entry in feed.entries:
            try:
                article = self._parse_entry(entry, source)
                
                # Filter by time range
                if article and self._is_in_time_range(article.published, start_time, end_time):
                    articles.append(article)
                    if self.logger:
                        self.logger.debug(f"Added article: {article.title}")
                
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to parse entry from {source.xml_url}: {e}")
                continue
        
        return articles
    
    def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL content with retry logic.
        
        Args:
            url: URL to fetch.
        
        Returns:
            Response content or None if failed.
        """
        for attempt in range(self.max_retries):
            try:
                if self.logger and attempt > 0:
                    self.logger.debug(f"Retry attempt {attempt + 1} for {url}")
                
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                return response.content
                
            except requests.exceptions.Timeout:
                if self.logger:
                    self.logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    if self.logger:
                        self.logger.log_network_error(url, "Timeout", "Request timed out after retries")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except requests.exceptions.RequestException as e:
                if self.logger:
                    self.logger.log_network_error(url, type(e).__name__, str(e))
                return None
        
        return None
    
    def _parse_entry(self, entry: Dict[str, Any], source) -> Optional[Article]:
        """Parse RSS entry into Article object.
        
        Args:
            entry: Feed entry dictionary.
            source: RSSSource object.
        
        Returns:
            Article object or None if parsing failed.
        """
        # Extract title
        title = entry.get('title', 'No Title')
        
        # Extract link
        link = entry.get('link', '')
        if not link:
            return None
        
        # Extract published time
        published = self._parse_published_time(entry)
        if not published:
            # If no published time, use current time
            published = datetime.now(pytz.UTC)
        
        # Extract description
        description = entry.get('summary', '') or entry.get('description', '')
        
        # Extract content (some feeds have full content)
        content = ''
        if 'content' in entry:
            content = entry.content[0].get('value', '') if entry.content else ''
        
        article = Article(
            title=title,
            link=link,
            published=published,
            description=description,
            source=source.title,
            source_url=source.xml_url,
            content=content
        )
        
        return article
    
    def _parse_published_time(self, entry: Dict[str, Any]) -> Optional[datetime]:
        """Parse published time from entry.
        
        Args:
            entry: Feed entry dictionary.
        
        Returns:
            Datetime object or None.
        """
        # Try different time fields
        time_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in time_fields:
            if field in entry and entry[field]:
                try:
                    time_tuple = entry[field]
                    dt = datetime(*time_tuple[:6])
                    # Assume UTC if no timezone
                    if dt.tzinfo is None:
                        dt = pytz.UTC.localize(dt)
                    return dt
                except Exception:
                    continue
        
        # Try string parsing
        for field in ['published', 'updated', 'created']:
            if field in entry and entry[field]:
                try:
                    from dateutil import parser
                    dt = parser.parse(entry[field])
                    if dt.tzinfo is None:
                        dt = pytz.UTC.localize(dt)
                    return dt
                except Exception:
                    continue
        
        return None
    
    def _is_in_time_range(self, check_time: datetime, start_time: datetime, 
                         end_time: datetime) -> bool:
        """Check if time is within range.
        
        Args:
            check_time: Time to check.
            start_time: Range start.
            end_time: Range end.
        
        Returns:
            True if in range, False otherwise.
        """
        # Ensure all times are timezone-aware
        if check_time.tzinfo is None:
            check_time = pytz.UTC.localize(check_time)
        if start_time.tzinfo is None:
            start_time = pytz.UTC.localize(start_time)
        if end_time.tzinfo is None:
            end_time = pytz.UTC.localize(end_time)
        
        return start_time <= check_time <= end_time
