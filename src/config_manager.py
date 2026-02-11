"""Configuration Manager Module

This module handles loading and validating configuration from YAML files.
"""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    """Configuration data model."""
    
    # Enterprise WeChat settings
    wecom_webhook_url: str = ""
    
    # RSS settings
    rss_file_path: str = "/Users/karenou/Desktop/AI/rss_article_fetcher/data/subscribe_rss.txt"
    
    # Network settings
    request_timeout: int = 30
    max_retries: int = 3
    concurrent_requests: int = 5
    
    # AI settings
    gemini_api_key: str = ""
    gemini_model: str = "gemini-pro"
    summary_min_length: int = 100
    summary_max_length: int = 300
    max_rpm: int = 3
    max_daily_requests: int = 15
    
    # Scheduler settings
    schedule_enabled: bool = False
    schedule_interval_hours: int = 24
    schedule_cron: str = ""
    
    # Storage settings
    data_dir: str = "/Users/karenou/Desktop/AI/rss_article_fetcher/data"
    log_dir: str = "/Users/karenou/Desktop/AI/rss_article_fetcher/logs"
    
    # Message settings
    batch_size: int = 10
    
    # Debug settings
    debug: bool = False


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. If None, uses default path.
        """
        if config_path is None:
            config_path = "/Users/karenou/Desktop/AI/rss_article_fetcher/config/config.yaml"
        
        self.config_path = config_path
        self.config = Config()
        
    def load_config(self) -> Config:
        """Load configuration from file.
        
        Returns:
            Config object with loaded settings.
        """
        if not os.path.exists(self.config_path):
            print(f"Warning: Configuration file not found at {self.config_path}")
            print("Using default configuration.")
            self._load_from_env()
            return self.config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if config_data:
                self._update_config(config_data)
            
            # Override with environment variables
            self._load_from_env()
            
            # Validate configuration
            self._validate_config()
            
            return self.config
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration.")
            self._load_from_env()
            return self.config
    
    def _update_config(self, config_data: Dict[str, Any]) -> None:
        """Update configuration from dictionary.
        
        Args:
            config_data: Dictionary containing configuration values.
        """
        # WeChat settings
        if 'wecom' in config_data:
            self.config.wecom_webhook_url = config_data['wecom'].get('webhook_url', self.config.wecom_webhook_url)
        
        # RSS settings
        if 'rss' in config_data:
            self.config.rss_file_path = config_data['rss'].get('file_path', self.config.rss_file_path)
        
        # Network settings
        if 'network' in config_data:
            self.config.request_timeout = config_data['network'].get('timeout', self.config.request_timeout)
            self.config.max_retries = config_data['network'].get('max_retries', self.config.max_retries)
            self.config.concurrent_requests = config_data['network'].get('concurrent_requests', self.config.concurrent_requests)
        
        # AI settings
        if 'ai' in config_data:
            self.config.gemini_api_key = config_data['ai'].get('gemini_api_key', self.config.gemini_api_key)
            self.config.gemini_model = config_data['ai'].get('gemini_model', self.config.gemini_model)
            self.config.summary_min_length = config_data['ai'].get('summary_min_length', self.config.summary_min_length)
            self.config.summary_max_length = config_data['ai'].get('summary_max_length', self.config.summary_max_length)
            self.config.max_rpm = config_data['ai'].get('max_rpm', self.config.max_rpm)
            self.config.max_daily_requests = config_data['ai'].get('max_daily_requests', self.config.max_daily_requests)
        
        # Scheduler settings
        if 'scheduler' in config_data:
            self.config.schedule_enabled = config_data['scheduler'].get('enabled', self.config.schedule_enabled)
            self.config.schedule_interval_hours = config_data['scheduler'].get('interval_hours', self.config.schedule_interval_hours)
            self.config.schedule_cron = config_data['scheduler'].get('cron', self.config.schedule_cron)
        
        # Storage settings
        if 'storage' in config_data:
            self.config.data_dir = config_data['storage'].get('data_dir', self.config.data_dir)
            self.config.log_dir = config_data['storage'].get('log_dir', self.config.log_dir)
        
        # Message settings
        if 'message' in config_data:
            self.config.batch_size = config_data['message'].get('batch_size', self.config.batch_size)
        
        # Debug settings
        if 'debug' in config_data:
            self.config.debug = config_data.get('debug', self.config.debug)
    
    def _load_from_env(self) -> None:
        """Load sensitive configuration from environment variables."""
        # Gemini API Key
        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key:
            self.config.gemini_api_key = gemini_key
        
        # WeChat Webhook URL
        wecom_url = os.getenv('WECOM_WEBHOOK_URL')
        if wecom_url:
            self.config.wecom_webhook_url = wecom_url
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        # Check if Gemini API key is set
        if not self.config.gemini_api_key:
            print("Warning: GEMINI_API_KEY is not set.")
            print("Please set it via environment variable or config file.")
            print("AI summarization features will not work without it.")
        
        # Check if WeChat webhook is set
        if not self.config.wecom_webhook_url:
            print("Warning: WeChat webhook URL is not set.")
            print("Push notifications will not work without it.")
        
        # Check if RSS file exists
        if not os.path.exists(self.config.rss_file_path):
            print(f"Warning: RSS file not found at {self.config.rss_file_path}")
        
        # Ensure directories exist
        os.makedirs(self.config.data_dir, exist_ok=True)
        os.makedirs(self.config.log_dir, exist_ok=True)
    
    def save_example_config(self, output_path: Optional[str] = None) -> None:
        """Save an example configuration file.
        
        Args:
            output_path: Path to save example config. If None, uses default.
        """
        if output_path is None:
            output_path = "/Users/karenou/Desktop/AI/rss_article_fetcher/config/config.yaml.example"
        
        example_config = {
            'wecom': {
                'webhook_url': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY_HERE'
            },
            'rss': {
                'file_path': '/Users/karenou/Desktop/AI/rss_article_fetcher/data/subscribe_rss.txt'
            },
            'network': {
                'timeout': 30,
                'max_retries': 3,
                'concurrent_requests': 5
            },
            'ai': {
                'gemini_api_key': 'YOUR_GEMINI_API_KEY_HERE',
                'gemini_model': 'gemini-pro',
                'summary_min_length': 100,
                'summary_max_length': 300,
                'max_rpm': 3,
                'max_daily_requests': 15
            },
            'scheduler': {
                'enabled': False,
                'interval_hours': 24,
                'cron': ''
            },
            'storage': {
                'data_dir': '/Users/karenou/Desktop/AI/rss_article_fetcher/data',
                'log_dir': '/Users/karenou/Desktop/AI/rss_article_fetcher/logs'
            },
            'message': {
                'batch_size': 10
            },
            'debug': False
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(example_config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"Example configuration saved to {output_path}")
