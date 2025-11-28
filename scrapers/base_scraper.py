"""
Base scraper class for service provider data collection.
Provides common functionality for all scrapers.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from playwright.sync_api import sync_playwright, Browser, Page
from bs4 import BeautifulSoup

import random


class BaseScraper(ABC):
    """Abstract base class for scrapers."""
    
    def __init__(self, config_path: str = "config/scraper_config.json"):
        """
        Initialize the scraper with configuration.
        
        Args:
            config_path: Path to scraper configuration JSON file
        """
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # List of modern User-Agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ]

    def _load_config(self, path: str) -> Dict:
        """Load scraper configuration from JSON file."""
        with open(path, 'r') as f:
            return json.load(f)
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        
        # Create logs directory if it doesn't exist
        log_file = Path(log_config.get('file', 'logs/scraper.log'))
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler() if log_config.get('console_output', True) else logging.NullHandler()
            ]
        )
        
        return logging.getLogger(self.__class__.__name__)
    
    def init_browser(self, proxy: Optional[str] = None) -> None:
        """Initialize Playwright browser instance."""
        self.logger.info("Initializing browser...")
        scraping_settings = self.config['scraping_settings']
        
        self.playwright = sync_playwright().start()
        
        # Access nested config correctly
        scraping_settings = self.config.get('scraping_settings', {})
        browser_config = scraping_settings.get('browser', {})
        
        launch_args = {
            'headless': browser_config.get('headless', False),
            'args': ['--disable-blink-features=AutomationControlled']
        }
        
        if proxy:
            launch_args['proxy'] = {'server': proxy}
            self.logger.info(f"Using proxy: {proxy}")
            
        self.browser = self.playwright.chromium.launch(**launch_args)
        
        # Select random User-Agent
        user_agent = random.choice(self.user_agents)
        self.logger.info(f"Using User-Agent: {user_agent}")
        
        self.context = self.browser.new_context(
            viewport=browser_config.get('viewport', {'width': 1920, 'height': 1080}),
            user_agent=user_agent
        )
        
        self.page = self.context.new_page()
        self.page.set_default_timeout(scraping_settings.get('timeout_seconds', 30) * 1000)
        
        self.logger.info("Browser initialized successfully")
    
    def close_browser(self) -> None:
        """Close browser and clean up resources."""
        if self.browser:
            self.logger.info("Closing browser...")
            self.browser.close()
            self.browser = None
            self.page = None
            
        if hasattr(self, 'playwright') and self.playwright:
            self.playwright.stop()
            self.playwright = None
    
    def rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        delay = self.config['scraping_settings'].get('rate_limit_seconds', 2.5)
        self.logger.debug(f"Rate limiting: waiting {delay} seconds")
        time.sleep(delay)
    
    def fetch_page(self, url: str, max_retries: Optional[int] = None) -> Optional[str]:
        """
        Fetch a page with retry logic.
        
        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts (overrides config)
            
        Returns:
            HTML content of the page or None if failed
        """
        if not self.page:
            self.init_browser()
        
        retries = max_retries or self.config['scraping_settings'].get('max_retries', 3)
        backoff = self.config['scraping_settings'].get('retry_backoff_factor', 2)
        
        for attempt in range(retries):
            try:
                self.logger.info(f"Fetching {url} (attempt {attempt + 1}/{retries})")
                self.page.goto(url, wait_until='networkidle')
                
                # Wait for content to load
                self.page.wait_for_load_state('domcontentloaded')
                
                html = self.page.content()
                self.logger.info(f"Successfully fetched {url}")
                return html
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                
                if attempt < retries - 1:
                    wait_time = backoff ** attempt
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to fetch {url} after {retries} attempts")
                    return None
        
        return None
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """
        Parse HTML content using BeautifulSoup.
        
        Args:
            html: Raw HTML string
            
        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, 'lxml')
    
    def save_html_snapshot(self, html: str, filename: str) -> None:
        """
        Save HTML snapshot for debugging and audit trail.
        
        Args:
            html: HTML content to save
            filename: Name of the file (without path)
        """
        if self.config['output_settings'].get('save_html_snapshots', True):
            snapshot_dir = Path(self.config['output_settings']['html_snapshot_dir'])
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = snapshot_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            
            self.logger.debug(f"Saved HTML snapshot: {filepath}")
    
    def save_data(self, data: List[Dict], country_code: str) -> str:
        """
        Save scraped data to JSON file.
        
        Args:
            data: List of data dictionaries to save
            country_code: Country code (e.g., 'BD', 'IN', 'US')
            
        Returns:
            Path to the saved file
        """
        output_settings = self.config['output_settings']
        raw_data_dir = Path(output_settings['raw_data_dir'])
        raw_data_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime(output_settings.get('timestamp_format', '%Y%m%d_%H%M%S'))
        filename = output_settings['filename_pattern'].format(
            country=country_code.lower(),
            timestamp=timestamp
        )
        
        filepath = raw_data_dir / filename
        
        # Add metadata
        output = {
            'metadata': {
                'country_code': country_code,
                'scrape_date': datetime.now().isoformat(),
                'total_records': len(data),
                'scraper_version': '1.0.0'
            },
            'providers': data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved {len(data)} records to {filepath}")
        return str(filepath)
    
    @abstractmethod
    def scrape(self) -> List[Dict]:
        """
        Main scraping method to be implemented by scrapers.
        
        Returns:
            List of provider data dictionaries
        """
        pass
    
    def run(self) -> str:
        """
        Execute the complete scraping workflow.
        
        Returns:
            Path to the saved data file
        """
        try:
            self.logger.info(f"Starting scraper: {self.__class__.__name__}")
            self.init_browser()
            
            data = self.scrape()
            
            self.logger.info(f"Scraping completed. Collected {len(data)} providers")
            
            # Get country code from config
            country_code = self._get_country_code()
            filepath = self.save_data(data, country_code)
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Scraping failed: {str(e)}", exc_info=True)
            raise
            
        finally:
            self.close_browser()
    
    @abstractmethod
    def _get_country_code(self) -> str:
        """Return the country code for this scraper (e.g., 'BD', 'IN', 'US')."""
        pass
