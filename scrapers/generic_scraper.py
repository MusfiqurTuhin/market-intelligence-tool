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
        Scrape providers based on configuration, including pagination and captcha handling.
        """
        self.logger.info(f"Starting scraper for {self.target_name} at {self.base_url}")
        
        all_providers_data = []
        current_url = self.base_url
        page_count = 0
        max_pages = 10
        
        while current_url and page_count < max_pages:
            page_count += 1
            self.logger.info(f"Scraping page {page_count}: {current_url}")
            
            retry_count = 0
            max_retries = 5
            html = None
            
            while retry_count < max_retries:
                html = self.fetch_page(current_url)
                
                if not html:
                    self.logger.warning(f"Failed to fetch page, retrying ({retry_count+1}/{max_retries})...")
                    self.restart_browser()
                    retry_count += 1
                    continue
                
                # Check for captcha
                if "It needs a human touch" in html or "Access Denied" in html:
                    self.logger.warning(f"Captcha/Block detected on page {page_count}, rotating proxy and retrying ({retry_count+1}/{max_retries})...")
                    self.restart_browser()
                    retry_count += 1
                    html = None # Reset html to ensure we don't process blocked page
                    continue
                
                break # Success
            
            if not html:
                self.logger.error(f"Failed to fetch page {page_count} after {max_retries} retries")
                break
            
            soup = self.parse_html(html)
            provider_urls = self._extract_provider_urls(soup)
            self.logger.info(f"Found {len(provider_urls)} providers on page {page_count}")
            
            if not provider_urls:
                self.logger.warning("No providers found (possible hidden block). Saving HTML for debugging.")
                debug_file = f"debug_fiverr_page_{page_count}.html"
                with open(debug_file, 'w') as f:
                    f.write(html)
                
                # If no providers found, maybe we should also retry?
                # For now, let's just continue to next page if possible, or stop.
                # But if listing is empty, next page link probably won't be there.
            
            # Scrape details for each provider
            for idx, url in enumerate(provider_urls, 1):
                self.logger.info(f"Scraping provider {idx}/{len(provider_urls)}: {url}")
                
                data = self._scrape_provider_detail(url)
                if data:
                    all_providers_data.append(data)
                
                # Rate limit within page
                if idx < len(provider_urls):
                    self.rate_limit()
            
            # Get next page URL
            next_url = self._get_next_page_url(soup)
            if next_url and next_url != current_url:
                current_url = next_url
                self.logger.info(f"Moving to next page: {current_url}")
                self.rate_limit()
            else:
                self.logger.info("No more pages found")
                break
        
        return all_providers_data

    def restart_browser(self):
        """Restart browser with new identity/proxy."""
        self.logger.info("Restarting browser...")
        self.close_browser()
        # Re-init with proxy enabled (assuming we want to rotate proxies)
        # We need to access the use_proxy flag. 
        # Since we modified BaseScraper to store self.use_proxy, we can use it.
        self.init_browser(use_proxy=getattr(self, 'use_proxy', True))

    def _get_next_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract next page URL."""
        selector = self.selectors.get('listing', {}).get('next_page')
        if not selector:
            return None
            
        link = soup.select_one(selector)
        if link:
            href = link.get('href')
            if href:
                return urljoin(self.base_url, href)
        return None
    
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


import argparse

def main():
    parser = argparse.ArgumentParser(description='Run generic scraper for a target.')
    parser.add_argument('target', help='Target name from scraper_config.json')
    parser.add_argument('--no-proxy', action='store_true', help='Disable proxy usage')
    args = parser.parse_args()

    try:
        scraper = GenericScraper(args.target)
        # We need to override the run method or modify it to accept args, 
        # but GenericScraper.run calls init_browser internally.
        # Let's modify GenericScraper.run to accept use_proxy.
        # For now, we can monkey patch or just modify BaseScraper.run signature in next step.
        # Actually, let's modify BaseScraper.run signature first.
        scraper.use_proxy = not args.no_proxy
        scraper.run()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
