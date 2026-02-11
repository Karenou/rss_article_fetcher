"""Time Parser Module

This module handles parsing and validating time range parameters.
"""

import argparse
from datetime import datetime, timedelta
from typing import Tuple, Optional
from dateutil import parser as date_parser
import pytz


class TimeParser:
    """Handles time range parameter parsing and validation."""
    
    def __init__(self, logger=None):
        """Initialize time parser.
        
        Args:
            logger: Logger instance.
        """
        self.logger = logger
    
    def parse_time_range(self, start_time: Optional[str] = None, 
                        end_time: Optional[str] = None,
                        default_hours: int = 24) -> Tuple[datetime, datetime]:
        """Parse time range from string inputs.
        
        Args:
            start_time: Start time string (various formats supported).
            end_time: End time string (various formats supported).
            default_hours: Default time range in hours if not specified.
        
        Returns:
            Tuple of (start_datetime, end_datetime) in UTC.
        
        Raises:
            ValueError: If time format is invalid or start > end.
        """
        now = datetime.now(pytz.UTC)
        
        # Parse end time (default to now)
        if end_time:
            try:
                end_dt = self._parse_datetime(end_time)
                if self.logger:
                    self.logger.debug(f"Parsed end time: {end_dt}")
            except Exception as e:
                error_msg = f"Invalid end time format: {end_time}. Error: {e}"
                if self.logger:
                    self.logger.error(error_msg)
                raise ValueError(error_msg)
        else:
            end_dt = now
            if self.logger:
                self.logger.debug(f"Using default end time (now): {end_dt}")
        
        # Parse start time (default to end_time - default_hours)
        if start_time:
            try:
                start_dt = self._parse_datetime(start_time)
                if self.logger:
                    self.logger.debug(f"Parsed start time: {start_dt}")
            except Exception as e:
                error_msg = f"Invalid start time format: {start_time}. Error: {e}"
                if self.logger:
                    self.logger.error(error_msg)
                raise ValueError(error_msg)
        else:
            start_dt = end_dt - timedelta(hours=default_hours)
            if self.logger:
                self.logger.debug(f"Using default start time ({default_hours}h ago): {start_dt}")
        
        # Validate time range
        if start_dt >= end_dt:
            error_msg = f"Start time ({start_dt}) must be before end time ({end_dt})"
            if self.logger:
                self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Convert to UTC
        start_dt_utc = self._to_utc(start_dt)
        end_dt_utc = self._to_utc(end_dt)
        
        if self.logger:
            self.logger.info(f"Time range: {start_dt_utc} to {end_dt_utc}")
            duration = end_dt_utc - start_dt_utc
            self.logger.info(f"Duration: {duration}")
        
        return start_dt_utc, end_dt_utc
    
    def _parse_datetime(self, time_str: str) -> datetime:
        """Parse datetime from string.
        
        Supports multiple formats:
        - YYYY-MM-DD
        - YYYY-MM-DD HH:MM:SS
        - ISO 8601 format
        - Relative times (e.g., "2 days ago", "1 hour ago")
        
        Args:
            time_str: Time string to parse.
        
        Returns:
            Parsed datetime object.
        
        Raises:
            ValueError: If format is not recognized.
        """
        time_str = time_str.strip()
        
        # Try to parse relative time
        if 'ago' in time_str.lower():
            return self._parse_relative_time(time_str)
        
        # Try standard datetime parsing
        try:
            dt = date_parser.parse(time_str)
            return dt
        except Exception as e:
            raise ValueError(f"Unable to parse time string: {time_str}. Error: {e}")
    
    def _parse_relative_time(self, time_str: str) -> datetime:
        """Parse relative time expressions.
        
        Args:
            time_str: Relative time string (e.g., "2 days ago").
        
        Returns:
            Datetime object.
        
        Raises:
            ValueError: If format is not recognized.
        """
        now = datetime.now(pytz.UTC)
        time_str = time_str.lower().strip()
        
        # Extract number and unit
        import re
        match = re.match(r'(\d+)\s*(hour|hours|day|days|week|weeks|minute|minutes)?\s*ago', time_str)
        
        if not match:
            raise ValueError(f"Invalid relative time format: {time_str}")
        
        amount = int(match.group(1))
        unit = match.group(2) or 'hours'
        
        if 'minute' in unit:
            delta = timedelta(minutes=amount)
        elif 'hour' in unit:
            delta = timedelta(hours=amount)
        elif 'day' in unit:
            delta = timedelta(days=amount)
        elif 'week' in unit:
            delta = timedelta(weeks=amount)
        else:
            raise ValueError(f"Unknown time unit: {unit}")
        
        return now - delta
    
    def _to_utc(self, dt: datetime) -> datetime:
        """Convert datetime to UTC.
        
        Args:
            dt: Datetime object.
        
        Returns:
            Datetime in UTC timezone.
        """
        if dt.tzinfo is None:
            # Assume local timezone
            dt = pytz.timezone('UTC').localize(dt)
        
        return dt.astimezone(pytz.UTC)
    
    def format_datetime(self, dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
        """Format datetime to string.
        
        Args:
            dt: Datetime object.
            format_str: Format string.
        
        Returns:
            Formatted datetime string.
        """
        return dt.strftime(format_str)
    
    def is_in_range(self, check_time: datetime, start_time: datetime, end_time: datetime) -> bool:
        """Check if a time is within a range.
        
        Args:
            check_time: Time to check.
            start_time: Range start time.
            end_time: Range end time.
        
        Returns:
            True if check_time is within range, False otherwise.
        """
        # Ensure all times are in UTC
        check_time_utc = self._to_utc(check_time)
        start_time_utc = self._to_utc(start_time)
        end_time_utc = self._to_utc(end_time)
        
        return start_time_utc <= check_time_utc <= end_time_utc


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser.
    
    Returns:
        ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description='RSS Article Fetcher - Fetch and summarize RSS articles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch articles from last 24 hours (default)
  python main.py
  
  # Fetch articles from specific date range
  python main.py --start "2024-01-01" --end "2024-01-02"
  
  # Fetch articles from last 2 days
  python main.py --start "2 days ago"
  
  # Fetch articles with custom time range
  python main.py --start "2024-01-01 10:00:00" --end "2024-01-01 18:00:00"
  
  # Force reprocess articles (ignore deduplication)
  python main.py --force
  
  # Run in debug mode
  python main.py --debug
        """
    )
    
    parser.add_argument(
        '--start',
        type=str,
        help='Start time (formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, "N days ago")',
        default=None
    )
    
    parser.add_argument(
        '--end',
        type=str,
        help='End time (formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS). Default: now',
        default=None
    )
    
    parser.add_argument(
        '--hours',
        type=int,
        help='Number of hours to look back (default: 24)',
        default=24
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file',
        default=None
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocess articles (ignore deduplication)',
        default=False
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode',
        default=False
    )
    
    parser.add_argument(
        '--no-push',
        action='store_true',
        help='Do not push to WeChat (dry run)',
        default=False
    )
    
    return parser
