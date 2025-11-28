"""Scrapers package for Odoo partner data collection."""

from .main_scraper_base import BaseScraper
from .main_scraper_bangladesh import BangladeshScraper

__all__ = ['BaseScraper', 'BangladeshScraper']
