"""
Generic scraper implementation that drives scraping based on configuration.
"""

from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper


class GenericScraper(BaseScraper):
    """Config-driven generic scraper."""
    
    def __init__(self, target_name: str, config_path: str = "config/scraper_config.json"):
        super().__init__(config_path)
        self.target_name = target_name
        self.target_config = self.config['targets'].get(target_name)
        
        if not self.target_config:
            raise ValueError(f"Target '{target_name}' not found in configuration")
            
        self.base_url = self.target_config['base_url']
        self.country_code = self.target_config.get('country_code', 'XX')
        self.selectors = self.target_config.get('selectors', {})
    
    def _get_country_code(self) -> str:
        return self.country_code
    
    def scrape(self) -> List[Dict]:
        """
        Scrape providers based on configuration.
        """
        self.logger.info(f"Starting scraper for {self.target_name} at {self.base_url}")
        
        html = self.fetch_page(self.base_url)
        if not html:
            self.logger.error("Failed to fetch listing page")
            return []
        
        soup = self.parse_html(html)
        provider_urls = self._extract_provider_urls(soup)
        self.logger.info(f"Found {len(provider_urls)} providers")
        
        providers_data = []
        for idx, url in enumerate(provider_urls, 1):
            self.logger.info(f"Scraping provider {idx}/{len(provider_urls)}: {url}")
            
            data = self._scrape_provider_detail(url)
            if data:
                providers_data.append(data)
            
            if idx < len(provider_urls):
                self.rate_limit()
        
        return providers_data
    
    def _extract_provider_urls(self, soup: BeautifulSoup) -> List[str]:
        """Extract provider URLs using configured selector."""
        urls = []
        selector = self.selectors.get('listing', {}).get('provider_link')
        
        if not selector:
            self.logger.warning("No provider_link selector configured")
            return []
            
        links = soup.select(selector)
        for link in links:
            href = link.get('href')
            if href:
                urls.append(urljoin(self.base_url, href))
                
        return list(set(urls))
    
    def _scrape_provider_detail(self, url: str) -> Optional[Dict]:
        """Scrape detail page using configured selectors."""
        html = self.fetch_page(url)
        if not html:
            return None
            
        soup = self.parse_html(html)
        detail_selectors = self.selectors.get('detail', {})
        
        data = {
            'source_url': url,
            'country': self.country_code,
            'name': self._extract_text(soup, detail_selectors.get('name')),
            'tier': self._extract_text(soup, detail_selectors.get('tier')),
            'location': self._extract_text(soup, detail_selectors.get('location')),
            'website': self._extract_attribute(soup, detail_selectors.get('website'), 'href'),
            'description': self._extract_text(soup, detail_selectors.get('description')),
            'services': self._extract_list(soup, detail_selectors.get('services')),
            'references': self._extract_list(soup, detail_selectors.get('references'))
        }
        
        return data

    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        if not selector:
            return ""
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else ""

    def _extract_attribute(self, soup: BeautifulSoup, selector: str, attribute: str) -> str:
        if not selector:
            return ""
        element = soup.select_one(selector)
        return element.get(attribute, "") if element else ""

    def _extract_list(self, soup: BeautifulSoup, selector: str) -> List[str]:
        if not selector:
            return []
        elements = soup.select(selector)
        return [el.get_text(strip=True) for el in elements]


def main():
    # Example usage
    try:
        scraper = GenericScraper("bangladesh")
        scraper.run()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
