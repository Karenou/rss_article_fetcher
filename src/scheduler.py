"""Scheduler Module

This module handles scheduled task execution.
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import os
import json


class Scheduler:
    """Manages scheduled task execution."""
    
    def __init__(self, config, logger=None):
        """Initialize scheduler.
        
        Args:
            config: Configuration object.
            logger: Logger instance.
        """
        self.config = config
        self.logger = logger
        self.scheduler = BlockingScheduler()
        self.last_run_file = os.path.join(config.data_dir, "last_run.json")
    
    def add_job(self, func, job_id: str = "rss_fetch_job"):
        """Add job to scheduler.
        
        Args:
            func: Function to execute.
            job_id: Job identifier.
        """
        if self.config.schedule_cron:
            # Use cron expression
            trigger = CronTrigger.from_crontab(self.config.schedule_cron)
            if self.logger:
                self.logger.info(f"Scheduled job with cron: {self.config.schedule_cron}")
        else:
            # Use interval
            trigger = IntervalTrigger(hours=self.config.schedule_interval_hours)
            if self.logger:
                self.logger.info(f"Scheduled job with interval: {self.config.schedule_interval_hours} hours")
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name="RSS Article Fetch Job",
            replace_existing=True
        )
    
    def start(self):
        """Start scheduler."""
        if self.logger:
            self.logger.info("Starting scheduler...")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            if self.logger:
                self.logger.info("Scheduler stopped by user")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Scheduler error: {e}", exc_info=True)
    
    def save_last_run(self):
        """Save last run timestamp."""
        try:
            data = {
                'last_run': datetime.now().isoformat()
            }
            with open(self.last_run_file, 'w') as f:
                json.dump(data, f)
            
            if self.logger:
                self.logger.debug(f"Saved last run timestamp: {data['last_run']}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save last run timestamp: {e}")
    
    def get_last_run(self) -> datetime:
        """Get last run timestamp.
        
        Returns:
            Last run datetime or None.
        """
        try:
            if os.path.exists(self.last_run_file):
                with open(self.last_run_file, 'r') as f:
                    data = json.load(f)
                
                from dateutil import parser
                last_run = parser.parse(data['last_run'])
                
                if self.logger:
                    self.logger.debug(f"Last run: {last_run}")
                
                return last_run
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load last run timestamp: {e}")
        
        return None
