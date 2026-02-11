"""WeChat Pusher Module

This module handles pushing article notifications to Enterprise WeChat.
"""

import requests
import json
from typing import List, Dict, Any
import time


class WeComPusher:
    """Pushes article notifications to Enterprise WeChat."""
    
    def __init__(self, webhook_url: str, batch_size: int = 10, 
                 max_retries: int = 3, logger=None):
        """Initialize WeChat pusher.
        
        Args:
            webhook_url: Enterprise WeChat webhook URL.
            batch_size: Maximum articles per message.
            max_retries: Maximum retry attempts.
            logger: Logger instance.
        """
        self.webhook_url = webhook_url
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.logger = logger
        self.enabled = bool(webhook_url)
        
        if not self.enabled and self.logger:
            self.logger.warning("WeChat webhook URL not configured, push disabled")
    
    def push_articles(self, articles: List) -> Dict[str, int]:
        """Push articles to WeChat.
        
        Args:
            articles: List of Article objects.
        
        Returns:
            Dictionary with success and failure counts.
        """
        if not self.enabled:
            if self.logger:
                self.logger.warning("WeChat push disabled, skipping")
            return {'success': 0, 'failed': 0, 'total': len(articles)}
        
        if not articles:
            if self.logger:
                self.logger.info("No articles to push")
            self._send_no_articles_message()
            return {'success': 0, 'failed': 0, 'total': 0}
        
        if self.logger:
            self.logger.info(f"Pushing {len(articles)} articles to WeChat")
        
        # Split into batches
        batches = self._create_batches(articles)
        
        success_count = 0
        failed_count = 0
        
        for i, batch in enumerate(batches):
            if self.logger:
                self.logger.info(f"Sending batch {i+1}/{len(batches)} ({len(batch)} articles)")
            
            if self._send_batch(batch, i+1, len(batches)):
                success_count += len(batch)
            else:
                failed_count += len(batch)
            
            # Small delay between batches
            if i < len(batches) - 1:
                time.sleep(2)
        
        stats = {
            'success': success_count,
            'failed': failed_count,
            'total': len(articles)
        }
        
        if self.logger:
            self.logger.info(f"Push complete: {success_count} success, {failed_count} failed")
        
        return stats
    
    def _create_batches(self, articles: List) -> List[List]:
        """Split articles into batches.
        
        Args:
            articles: List of Article objects.
        
        Returns:
            List of article batches.
        """
        batches = []
        for i in range(0, len(articles), self.batch_size):
            batch = articles[i:i + self.batch_size]
            batches.append(batch)
        return batches
    
    def _send_batch(self, articles: List, batch_num: int, total_batches: int) -> bool:
        """Send a batch of articles.
        
        Args:
            articles: List of Article objects.
            batch_num: Current batch number.
            total_batches: Total number of batches.
        
        Returns:
            True if successful, False otherwise.
        """
        # Format message
        message = self._format_message(articles, batch_num, total_batches)
        
        # Send with retry
        for attempt in range(self.max_retries):
            try:
                if self.logger and attempt > 0:
                    self.logger.debug(f"Retry attempt {attempt + 1} for batch {batch_num}")
                
                response = requests.post(
                    self.webhook_url,
                    json=message,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                response.raise_for_status()
                
                result = response.json()
                
                if result.get('errcode') == 0:
                    if self.logger:
                        self.logger.info(f"Batch {batch_num} sent successfully")
                    return True
                else:
                    if self.logger:
                        self.logger.error(f"WeChat API error: {result.get('errmsg')}")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        return False
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to send batch {batch_num}: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return False
        
        return False
    
    def _format_message(self, articles: List, batch_num: int, total_batches: int) -> Dict[str, Any]:
        """Format articles into WeChat message.
        
        Args:
            articles: List of Article objects.
            batch_num: Current batch number.
            total_batches: Total number of batches.
        
        Returns:
            Message dictionary.
        """
        # Build markdown content
        content_parts = []
        
        # Header
        if total_batches > 1:
            content_parts.append(f"# 📰 RSS Article Updates (Batch {batch_num}/{total_batches})\n")
        else:
            content_parts.append(f"# 📰 RSS Article Updates\n")
        
        content_parts.append(f"Found **{len(articles)}** new articles\n")
        content_parts.append("---\n")
        
        # Articles
        for i, article in enumerate(articles, 1):
            content_parts.append(f"\n### {i}. {article.title}\n")
            content_parts.append(f"**Source:** {article.source}\n")
            content_parts.append(f"**Link:** [{article.link}]({article.link})\n")
            
            # Prefer Chinese summary, fallback to English summary
            summary_text = getattr(article, 'summary_zh', '') or article.summary
            if summary_text:
                # Truncate summary if too long
                if len(summary_text) > 500:
                    summary_text = summary_text[:500] + "..."
                content_parts.append(f"\n**Summary:**\n{summary_text}\n")
            
            if i < len(articles):
                content_parts.append("\n---\n")
        
        content = "".join(content_parts)
        
        # WeChat message format
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        return message
    
    def _send_no_articles_message(self) -> bool:
        """Send message when no new articles found.
        
        Returns:
            True if successful, False otherwise.
        """
        if not self.enabled:
            return False
        
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": "# 📰 RSS Article Updates\n\nNo new articles found in the specified time range."
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result.get('errcode') == 0
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to send no-articles message: {e}")
            return False
    
    def send_test_message(self) -> bool:
        """Send a test message to verify webhook.
        
        Returns:
            True if successful, False otherwise.
        """
        if not self.enabled:
            if self.logger:
                self.logger.error("WeChat webhook not configured")
            return False
        
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": "# 🧪 Test Message\n\nRSS Article Fetcher is configured correctly!"
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('errcode') == 0:
                if self.logger:
                    self.logger.info("Test message sent successfully")
                return True
            else:
                if self.logger:
                    self.logger.error(f"Test message failed: {result.get('errmsg')}")
                return False
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to send test message: {e}")
            return False
    
    def send_summary(self, stats: Dict[str, Any]) -> bool:
        """Send execution summary.
        
        Args:
            stats: Statistics dictionary.
        
        Returns:
            True if successful, False otherwise.
        """
        if not self.enabled:
            return False
        
        content_parts = [
            "# 📊 Execution Summary\n",
            f"**RSS Sources:** {stats.get('sources_count', 0)}\n",
            f"**Articles Fetched:** {stats.get('articles_fetched', 0)}\n",
            f"**New Articles:** {stats.get('new_articles', 0)}\n",
            f"**Articles Pushed:** {stats.get('articles_pushed', 0)}\n",
            f"**Duration:** {stats.get('duration', 'N/A')}\n"
        ]
        
        content = "".join(content_parts)
        
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            response.raise_for_status()
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to send summary: {e}")
            return False
