"""Content Fetcher Module

This module handles fetching and extracting article content from web pages.
"""

import requests
from bs4 import BeautifulSoup
from newspaper import Article as NewspaperArticle
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class ContentFetcher:
    """Fetches and extracts article content from web pages."""
    
    def __init__(self, timeout: int = 30, concurrent_requests: int = 5, logger=None):
        """Initialize content fetcher.
        
        Args:
            timeout: Request timeout in seconds.
            concurrent_requests: Number of concurrent requests.
            logger: Logger instance.
        """
        self.timeout = timeout
        self.concurrent_requests = concurrent_requests
        self.logger = logger
        
        # Set up session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def fetch_articles_content(self, articles: List) -> List:
        """Fetch content for multiple articles concurrently.
        
        Args:
            articles: List of Article objects.
        
        Returns:
            List of Article objects with content filled.
        """
        if self.logger:
            self.logger.info(f"Fetching content for {len(articles)} articles")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.concurrent_requests) as executor:
            # Submit all tasks
            future_to_article = {
                executor.submit(self._fetch_article_content, article): article 
                for article in articles
            }
            
            # Process completed tasks
            for future in as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    updated_article = future.result()
                    results.append(updated_article)
                    
                    if self.logger:
                        status = "success" if updated_article.content else "failed"
                        self.logger.log_article_processing(
                            updated_article.title,
                            updated_article.link,
                            status
                        )
                        
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error processing article {article.link}: {e}")
                    results.append(article)
        
        if self.logger:
            success_count = sum(1 for a in results if a.content)
            self.logger.info(f"Successfully fetched content for {success_count}/{len(articles)} articles")
        
        return results
    
    def _fetch_article_content(self, article):
        """Fetch content for a single article.
        
        Args:
            article: Article object.
        
        Returns:
            Article object with content filled.
        """
        try:
            # Try newspaper3k first (better extraction)
            content = self._fetch_with_newspaper(article.link)
            
            if content:
                article.content = content
                return article
            
            # Fallback to BeautifulSoup
            if self.logger:
                self.logger.debug(f"Newspaper3k failed for {article.link}, trying BeautifulSoup")
            
            content = self._fetch_with_beautifulsoup(article.link)
            
            if content:
                article.content = content
                return article
            
            # If both failed, use RSS description as fallback
            if self.logger:
                self.logger.warning(f"Failed to extract content for {article.link}, using RSS description")
            
            article.content = article.description or article.title
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error fetching content for {article.link}: {e}")
            article.content = article.description or article.title
        
        return article
    
    def _fetch_with_newspaper(self, url: str) -> Optional[str]:
        """Fetch article content using newspaper3k.
        
        Args:
            url: Article URL.
        
        Returns:
            Extracted text content or None.
        """
        try:
            article = NewspaperArticle(url)
            article.download()
            article.parse()
            
            if article.text and len(article.text) > 100:
                return article.text
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Newspaper3k extraction failed for {url}: {e}")
            return None
    
    def _fetch_with_beautifulsoup(self, url: str) -> Optional[str]:
        """Fetch article content using BeautifulSoup.
        
        Args:
            url: Article URL.
        
        Returns:
            Extracted text content or None.
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 
                                'aside', 'iframe', 'noscript', 'form']):
                element.decompose()
            
            # Try to find main content
            content = self._extract_main_content(soup)
            
            if content and len(content) > 100:
                return content
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"BeautifulSoup extraction failed for {url}: {e}")
            return None
    
    def _extract_main_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract main content from parsed HTML.
        
        Args:
            soup: BeautifulSoup object.
        
        Returns:
            Extracted text or None.
        """
        # Try common content containers
        content_selectors = [
            'article',
            '[role="main"]',
            '.post-content',
            '.article-content',
            '.entry-content',
            '.content',
            'main',
            '#content',
            '.post-body',
            '.article-body'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # Get text from all matching elements
                texts = []
                for element in elements:
                    text = element.get_text(separator='\n', strip=True)
                    if text:
                        texts.append(text)
                
                if texts:
                    combined_text = '\n\n'.join(texts)
                    if len(combined_text) > 100:
                        return combined_text
        
        # Fallback: get all paragraph text
        paragraphs = soup.find_all('p')
        if paragraphs:
            text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            if len(text) > 100:
                return text
        
        # Last resort: get all text
        text = soup.get_text(separator='\n', strip=True)
        if len(text) > 100:
            # Clean up excessive whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)
        
        return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text.
        
        Args:
            text: Raw text.
        
        Returns:
            Cleaned text.
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        # Remove excessive newlines
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')
        
        return text.strip()
