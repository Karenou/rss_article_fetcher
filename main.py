#!/usr/bin/env python3
"""RSS Article Fetcher - Main Program

This program fetches RSS articles, generates summaries, and pushes to WeChat.
"""

import sys
import os
from datetime import datetime, timedelta

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config_manager import ConfigManager
from src.logger import get_logger
from src.rss_manager import RSSManager
from src.time_parser import TimeParser, create_argument_parser
from src.rss_fetcher import RSSFetcher
from src.content_fetcher import ContentFetcher
from src.summarizer import Summarizer
from src.storage import Storage
from src.wecom_pusher import WeComPusher
from src.scheduler import Scheduler


class RSSArticleFetcher:
    """Main application class."""
    
    def __init__(self, config_path=None, debug=False):
        """Initialize application.
        
        Args:
            config_path: Path to configuration file.
            debug: Enable debug mode.
        """
        # Load configuration
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Override debug setting from command line
        if debug:
            self.config.debug = debug
        
        # Initialize logger
        self.logger = get_logger(
            log_dir=self.config.log_dir,
            debug=self.config.debug
        )
        
        # Initialize components
        self.rss_manager = RSSManager(self.config.rss_file_path, self.logger)
        self.time_parser = TimeParser(self.logger)
        self.rss_fetcher = RSSFetcher(
            timeout=self.config.request_timeout,
            max_retries=self.config.max_retries,
            logger=self.logger
        )
        self.content_fetcher = ContentFetcher(
            timeout=self.config.request_timeout,
            concurrent_requests=self.config.concurrent_requests,
            logger=self.logger
        )
        self.summarizer = Summarizer(
            api_key=self.config.gemini_api_key,
            model_name=self.config.gemini_model,
            min_length=self.config.summary_min_length,
            max_length=self.config.summary_max_length,
            max_rpm=self.config.max_rpm,
            max_daily_requests=self.config.max_daily_requests,
            data_dir=self.config.data_dir,
            logger=self.logger
        )
        self.storage = Storage(self.config.data_dir, self.logger)
        self.wecom_pusher = WeComPusher(
            webhook_url=self.config.wecom_webhook_url,
            batch_size=self.config.batch_size,
            logger=self.logger
        )
    
    def run(self, start_time=None, end_time=None, force=False, no_push=False):
        """Run the article fetching process.
        
        Args:
            start_time: Start time string.
            end_time: End time string.
            force: Force reprocess articles.
            no_push: Skip WeChat push (dry run).
        
        Returns:
            Statistics dictionary.
        """
        start_dt = datetime.now()
        
        # Log startup
        self.logger.log_startup({
            'rss_file': self.config.rss_file_path,
            'data_dir': self.config.data_dir,
            'log_dir': self.config.log_dir,
            'gemini_model': self.config.gemini_model,
            'batch_size': self.config.batch_size,
            'force_mode': force,
            'dry_run': no_push
        })
        
        try:
            # Step 1: Load RSS sources
            self.logger.info("Step 1: Loading RSS sources...")
            sources = self.rss_manager.load_sources()
            self.rss_manager.validate_sources()
            
            # Step 2: Parse time range
            self.logger.info("Step 2: Parsing time range...")
            start_time_dt, end_time_dt = self.time_parser.parse_time_range(
                start_time, end_time, self.config.schedule_interval_hours
            )
            
            # Step 3: Fetch articles from RSS feeds
            self.logger.info("Step 3: Fetching articles from RSS feeds...")
            articles = self.rss_fetcher.fetch_articles(sources, start_time_dt, end_time_dt)
            
            if not articles:
                self.logger.info("No articles found in time range")
                stats = self._create_stats(start_dt, len(sources), 0, 0, 0)
                self.logger.log_summary(stats)
                
                if not no_push:
                    self.wecom_pusher.push_articles([])
                
                return stats
            
            # Step 4: Filter out already processed articles
            self.logger.info("Step 4: Filtering processed articles...")
            new_articles = self.storage.filter_unprocessed(articles, force)
            
            if not new_articles:
                self.logger.info("No new articles to process")
                stats = self._create_stats(start_dt, len(sources), len(articles), 0, 0)
                self.logger.log_summary(stats)
                return stats
            
            # Step 5: Fetch article content
            self.logger.info("Step 5: Fetching article content...")
            articles_with_content = self.content_fetcher.fetch_articles_content(new_articles)
            
            # Step 6: Generate summaries
            self.logger.info("Step 6: Generating English summaries...")
            articles_with_summaries = self.summarizer.summarize_articles(articles_with_content)
            
            # Step 7: Save to database
            self.logger.info("Step 7: Saving articles to database...")
            self.storage.save_articles(articles_with_summaries)
            
            # Step 8: Push to WeChat
            if no_push:
                self.logger.info("Step 8: Skipping WeChat push (dry run mode)")
                push_stats = {'success': 0, 'failed': 0, 'total': len(articles_with_summaries)}
            else:
                self.logger.info("Step 8: Pushing to WeChat...")
                push_stats = self.wecom_pusher.push_articles(articles_with_summaries)
            
            # Create statistics
            end_dt = datetime.now()
            duration = end_dt - start_dt
            
            stats = {
                'sources_count': len(sources),
                'articles_fetched': len(articles),
                'new_articles': len(new_articles),
                'articles_pushed': push_stats['success'],
                'push_failed': push_stats['failed'],
                'duration': str(duration).split('.')[0],
                'start_time': start_time_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time_dt.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Log summary
            self.logger.log_summary(stats)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Fatal error during execution: {e}", exc_info=True)
            raise
    
    def _create_stats(self, start_dt, sources_count, articles_fetched, 
                     new_articles, articles_pushed):
        """Create statistics dictionary.
        
        Args:
            start_dt: Start datetime.
            sources_count: Number of RSS sources.
            articles_fetched: Number of articles fetched.
            new_articles: Number of new articles.
            articles_pushed: Number of articles pushed.
        
        Returns:
            Statistics dictionary.
        """
        end_dt = datetime.now()
        duration = end_dt - start_dt
        
        return {
            'sources_count': sources_count,
            'articles_fetched': articles_fetched,
            'new_articles': new_articles,
            'articles_pushed': articles_pushed,
            'duration': str(duration).split('.')[0]
        }
    
    def push_only(self, start_time=None, end_time=None):
        """Push saved articles from database without re-fetching.
        
        Args:
            start_time: Start time string.
            end_time: End time string.
        
        Returns:
            Statistics dictionary.
        """
        start_dt = datetime.now()
        
        self.logger.info("Running in push-only mode (no RSS fetching)")
        
        try:
            # Step 1: Parse time range
            self.logger.info("Step 1: Parsing time range...")
            start_time_dt, end_time_dt = self.time_parser.parse_time_range(
                start_time, end_time, self.config.schedule_interval_hours
            )
            
            # Step 2: Query articles from database
            self.logger.info("Step 2: Querying articles from database...")
            start_str = start_time_dt.strftime('%Y-%m-%d %H:%M:%S')
            end_str = end_time_dt.strftime('%Y-%m-%d %H:%M:%S')
            articles = self.storage.get_articles_by_time_range(start_str, end_str)
            
            if not articles:
                self.logger.info("No articles found in database for the given time range")
                self.wecom_pusher.push_articles([])
                return self._create_stats(start_dt, 0, 0, 0, 0)
            
            self.logger.info(f"Found {len(articles)} articles in database")
            
            # Step 3: Push to WeChat
            self.logger.info("Step 3: Pushing to WeChat...")
            push_stats = self.wecom_pusher.push_articles(articles)
            
            # Create statistics
            end_dt_now = datetime.now()
            duration = end_dt_now - start_dt
            
            stats = {
                'sources_count': 0,
                'articles_fetched': len(articles),
                'new_articles': len(articles),
                'articles_pushed': push_stats['success'],
                'push_failed': push_stats['failed'],
                'duration': str(duration).split('.')[0],
                'start_time': start_time_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'mode': 'push-only'
            }
            
            self.logger.log_summary(stats)
            return stats
            
        except Exception as e:
            self.logger.error(f"Fatal error during push-only execution: {e}", exc_info=True)
            raise

    def run_scheduled(self):
        """Run in scheduled mode."""
        self.logger.info("Starting in scheduled mode")
        
        scheduler = Scheduler(self.config, self.logger)
        
        def scheduled_job():
            """Job function for scheduler."""
            try:
                # Get last run time
                last_run = scheduler.get_last_run()
                
                if last_run:
                    # Use last run as start time
                    start_time = last_run.strftime('%Y-%m-%d %H:%M:%S')
                    end_time = None
                else:
                    # First run, use default interval
                    start_time = None
                    end_time = None
                
                # Run fetcher
                self.run(start_time=start_time, end_time=end_time)
                
                # Save last run time
                scheduler.save_last_run()
                
            except Exception as e:
                self.logger.error(f"Scheduled job failed: {e}", exc_info=True)
        
        # Add job to scheduler
        scheduler.add_job(scheduled_job)
        
        # Run once immediately
        self.logger.info("Running initial fetch...")
        scheduled_job()
        
        # Start scheduler
        scheduler.start()


def main():
    """Main entry point."""
    # Parse arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    try:
        # Create fetcher instance
        fetcher = RSSArticleFetcher(config_path=args.config, debug=args.debug)
        
        # Check run mode
        if args.push_only:
            # Push-only mode: read from database, no RSS fetching
            fetcher.push_only(
                start_time=args.start,
                end_time=args.end
            )
        elif fetcher.config.schedule_enabled:
            fetcher.run_scheduled()
        else:
            # Normal mode: fetch + process + push
            fetcher.run(
                start_time=args.start,
                end_time=args.end,
                force=args.force,
                no_push=args.no_push
            )
        
        return 0
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
