"""Storage Module

This module handles data persistence and deduplication using SQLite.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Set, Optional
import hashlib


class Storage:
    """Manages article storage and deduplication."""
    
    def __init__(self, data_dir: str, logger=None):
        """Initialize storage.
        
        Args:
            data_dir: Directory for data storage.
            logger: Logger instance.
        """
        self.data_dir = data_dir
        self.logger = logger
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Database path
        self.db_path = os.path.join(data_dir, "processed_articles.db")
        
        # Initialize database
        self._init_database()
        
        # In-memory cache for faster lookups
        self.processed_urls: Set[str] = set()
        self._load_processed_urls()
    
    def _init_database(self) -> None:
        """Initialize SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create articles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    url_hash TEXT UNIQUE NOT NULL,
                    title TEXT,
                    title_zh TEXT,
                    source TEXT,
                    source_url TEXT,
                    description TEXT,
                    content TEXT,
                    summary TEXT,
                    summary_zh TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    published_at TIMESTAMP
                )
            ''')
            
            # Add new columns if they don't exist (for backward compatibility)
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN description TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN source_url TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN content TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN summary TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN title_zh TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN summary_zh TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Create index on url_hash for faster lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_url_hash 
                ON articles(url_hash)
            ''')
            
            # Create index on processed_at for cleanup queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_processed_at 
                ON articles(processed_at)
            ''')
            
            conn.commit()
            conn.close()
            
            if self.logger:
                self.logger.info(f"Database initialized at {self.db_path}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise
    
    def _load_processed_urls(self) -> None:
        """Load processed URLs into memory cache."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT url_hash FROM articles")
            rows = cursor.fetchall()
            
            self.processed_urls = {row[0] for row in rows}
            
            conn.close()
            
            if self.logger:
                self.logger.info(f"Loaded {len(self.processed_urls)} processed articles from database")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load processed URLs: {e}")
            self.processed_urls = set()
    
    def _hash_url(self, url: str) -> str:
        """Generate hash for URL.
        
        Args:
            url: Article URL.
        
        Returns:
            SHA256 hash of URL.
        """
        return hashlib.sha256(url.encode('utf-8')).hexdigest()
    
    def is_processed(self, url: str) -> bool:
        """Check if article has been processed.
        
        Args:
            url: Article URL.
        
        Returns:
            True if already processed, False otherwise.
        """
        url_hash = self._hash_url(url)
        return url_hash in self.processed_urls
    
    def mark_as_processed(self, article) -> bool:
        """Mark article as processed.
        
        Args:
            article: Article object.
        
        Returns:
            True if successfully saved, False otherwise.
        """
        try:
            url_hash = self._hash_url(article.link)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert datetime to string
            published_at = article.published.isoformat() if article.published else None
            
            # Get all fields from article
            description = getattr(article, 'description', '') or ''
            source_url = getattr(article, 'source_url', '') or ''
            content = getattr(article, 'content', '') or ''
            summary = getattr(article, 'summary', '') or ''
            title_zh = getattr(article, 'title_zh', '') or ''
            summary_zh = getattr(article, 'summary_zh', '') or ''
            
            cursor.execute('''
                INSERT OR IGNORE INTO articles 
                (url, url_hash, title, title_zh, source, source_url, description, content, summary, summary_zh, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (article.link, url_hash, article.title, title_zh, article.source, 
                  source_url, description, content, summary, summary_zh, published_at))
            
            conn.commit()
            conn.close()
            
            # Update cache
            self.processed_urls.add(url_hash)
            
            if self.logger:
                self.logger.debug(f"Marked as processed: {article.link}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to mark article as processed: {e}")
            return False
    
    def filter_unprocessed(self, articles: List, force: bool = False) -> List:
        """Filter out already processed articles.
        
        Args:
            articles: List of Article objects.
            force: If True, skip deduplication.
        
        Returns:
            List of unprocessed Article objects.
        """
        if force:
            if self.logger:
                self.logger.info("Force mode enabled, skipping deduplication")
            return articles
        
        unprocessed = []
        skipped_count = 0
        
        for article in articles:
            if not self.is_processed(article.link):
                unprocessed.append(article)
            else:
                skipped_count += 1
                if self.logger:
                    self.logger.debug(f"Skipping already processed article: {article.title}")
        
        if self.logger:
            self.logger.info(f"Filtered articles: {len(unprocessed)} new, {skipped_count} already processed")
        
        return unprocessed
    
    def save_articles(self, articles: List) -> int:
        """Save multiple articles as processed.
        
        Args:
            articles: List of Article objects.
        
        Returns:
            Number of articles successfully saved.
        """
        success_count = 0
        
        for article in articles:
            if self.mark_as_processed(article):
                success_count += 1
        
        if self.logger:
            self.logger.info(f"Saved {success_count}/{len(articles)} articles to database")
        
        return success_count
    
    def get_articles_by_time_range(self, start_time: str, end_time: str) -> List:
        """Query saved articles from database by time range.
        
        Args:
            start_time: Start time string (ISO format, e.g. '2026-02-10 00:00:00').
            end_time: End time string (ISO format, e.g. '2026-02-11 17:00:00').
        
        Returns:
            List of Article objects.
        """
        from src.rss_fetcher import Article
        from dateutil import parser as date_parser
        import pytz

        articles = []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT title, title_zh, url AS link, source, source_url, 
                       description, content, summary, summary_zh, published_at
                FROM articles
                WHERE published_at >= ? AND published_at <= ?
                ORDER BY published_at DESC
            ''', (start_time, end_time))

            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                # Parse published_at back to datetime
                published = None
                if row['published_at']:
                    try:
                        published = date_parser.parse(row['published_at'])
                        if published.tzinfo is None:
                            published = pytz.UTC.localize(published)
                    except Exception:
                        published = datetime.now(pytz.UTC)

                article = Article(
                    title=row['title'] or '',
                    link=row['link'] or '',
                    published=published or datetime.now(pytz.UTC),
                    description=row['description'] or '',
                    source=row['source'] or '',
                    source_url=row['source_url'] or '',
                    content=row['content'] or '',
                    summary=row['summary'] or '',
                    summary_zh=row['summary_zh'] or '',
                    title_zh=row['title_zh'] or ''
                )
                articles.append(article)

            if self.logger:
                self.logger.info(
                    f"Queried {len(articles)} articles from database "
                    f"(range: {start_time} ~ {end_time})"
                )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to query articles by time range: {e}", exc_info=True)

        return articles

    def get_statistics(self) -> dict:
        """Get storage statistics.
        
        Returns:
            Dictionary with statistics.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total articles
            cursor.execute("SELECT COUNT(*) FROM articles")
            total = cursor.fetchone()[0]
            
            # Articles by source
            cursor.execute('''
                SELECT source, COUNT(*) as count 
                FROM articles 
                GROUP BY source 
                ORDER BY count DESC 
                LIMIT 10
            ''')
            by_source = cursor.fetchall()
            
            # Recent articles (last 7 days)
            cursor.execute('''
                SELECT COUNT(*) FROM articles 
                WHERE processed_at >= datetime('now', '-7 days')
            ''')
            recent = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_articles': total,
                'recent_articles_7days': recent,
                'top_sources': by_source
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def cleanup_old_records(self, days: int = 90) -> int:
        """Clean up old records from database.
        
        Args:
            days: Remove records older than this many days.
        
        Returns:
            Number of records deleted.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM articles 
                WHERE processed_at < datetime('now', ? || ' days')
            ''', (f'-{days}',))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            # Reload cache
            self._load_processed_urls()
            
            if self.logger:
                self.logger.info(f"Cleaned up {deleted} old records (older than {days} days)")
            
            return deleted
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to cleanup old records: {e}")
            return 0
    
    def reset_database(self) -> bool:
        """Reset database (delete all records).
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM articles")
            conn.commit()
            conn.close()
            
            # Clear cache
            self.processed_urls.clear()
            
            if self.logger:
                self.logger.info("Database reset successfully")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to reset database: {e}")
            return False
