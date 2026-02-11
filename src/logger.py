"""Logger Module

This module provides logging functionality for the RSS Article Fetcher.
"""

import logging
import os
from datetime import datetime
from typing import Optional


class Logger:
    """Custom logger for RSS Article Fetcher."""
    
    def __init__(self, name: str = "rss_fetcher", log_dir: Optional[str] = None, debug: bool = False):
        """Initialize logger.
        
        Args:
            name: Logger name.
            log_dir: Directory to store log files.
            debug: Enable debug mode.
        """
        self.name = name
        self.log_dir = log_dir or "/Users/karenou/Desktop/AI/rss_article_fetcher/logs"
        self.debug_mode = debug
        
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        console_handler.setFormatter(simple_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler - daily log file
        log_filename = f"rss_fetcher_{datetime.now().strftime('%Y%m%d')}.log"
        log_filepath = os.path.join(self.log_dir, log_filename)
        
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)
        
        # Error file handler - separate file for errors
        error_log_filename = f"rss_fetcher_error_{datetime.now().strftime('%Y%m%d')}.log"
        error_log_filepath = os.path.join(self.log_dir, error_log_filename)
        
        error_handler = logging.FileHandler(error_log_filepath, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(error_handler)
    
    def info(self, message: str) -> None:
        """Log info message.
        
        Args:
            message: Message to log.
        """
        self.logger.info(message)
    
    def error(self, message: str, exc_info: bool = False) -> None:
        """Log error message.
        
        Args:
            message: Message to log.
            exc_info: Include exception information.
        """
        self.logger.error(message, exc_info=exc_info)
    
    def warning(self, message: str) -> None:
        """Log warning message.
        
        Args:
            message: Message to log.
        """
        self.logger.warning(message)
    
    def debug(self, message: str) -> None:
        """Log debug message.
        
        Args:
            message: Message to log.
        """
        self.logger.debug(message)
    
    def log_startup(self, config: dict) -> None:
        """Log startup information.
        
        Args:
            config: Configuration dictionary.
        """
        self.info("=" * 60)
        self.info("RSS Article Fetcher Starting")
        self.info("=" * 60)
        self.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.info(f"Debug Mode: {self.debug_mode}")
        self.info(f"Log Directory: {self.log_dir}")
        
        # Log key configuration (without sensitive data)
        self.info("Configuration:")
        for key, value in config.items():
            # Hide sensitive information
            if 'key' in key.lower() or 'password' in key.lower() or 'token' in key.lower():
                self.info(f"  {key}: ***HIDDEN***")
            elif 'webhook' in key.lower():
                # Show only last part of webhook URL
                if value and len(value) > 20:
                    self.info(f"  {key}: ...{value[-20:]}")
                else:
                    self.info(f"  {key}: {value}")
            else:
                self.info(f"  {key}: {value}")
        
        self.info("-" * 60)
    
    def log_summary(self, stats: dict) -> None:
        """Log execution summary.
        
        Args:
            stats: Statistics dictionary containing execution results.
        """
        self.info("=" * 60)
        self.info("Execution Summary")
        self.info("=" * 60)
        
        for key, value in stats.items():
            self.info(f"{key}: {value}")
        
        self.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.info("=" * 60)
    
    def log_rss_source_error(self, source_url: str, error: Exception) -> None:
        """Log RSS source access error.
        
        Args:
            source_url: URL of the RSS source.
            error: Exception that occurred.
        """
        self.error(f"Failed to fetch RSS source: {source_url}")
        self.error(f"Error type: {type(error).__name__}")
        self.error(f"Error message: {str(error)}")
    
    def log_article_processing(self, article_title: str, article_url: str, status: str) -> None:
        """Log article processing status.
        
        Args:
            article_title: Title of the article.
            article_url: URL of the article.
            status: Processing status (success/failed/skipped).
        """
        self.info(f"Article [{status}]: {article_title}")
        self.debug(f"  URL: {article_url}")
    
    def log_network_error(self, url: str, error_type: str, error_message: str) -> None:
        """Log network error.
        
        Args:
            url: URL that failed.
            error_type: Type of error.
            error_message: Error message.
        """
        self.error(f"Network error accessing: {url}")
        self.error(f"Error type: {error_type}")
        self.error(f"Error message: {error_message}")


def get_logger(name: str = "rss_fetcher", log_dir: Optional[str] = None, debug: bool = False) -> Logger:
    """Get or create a logger instance.
    
    Args:
        name: Logger name.
        log_dir: Directory to store log files.
        debug: Enable debug mode.
    
    Returns:
        Logger instance.
    """
    return Logger(name=name, log_dir=log_dir, debug=debug)
