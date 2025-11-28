import requests
import random
import logging
from typing import Optional, List

class ProxyManager:
    def __init__(self):
        self.logger = logging.getLogger('ProxyManager')
        self.proxies = []
        self.current_proxy_index = 0
        self.sources = [
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
        ]

    def fetch_proxies(self):
        """Fetch free proxies from public sources."""
        self.logger.info("Fetching free proxies...")
        found_proxies = set()
        
        for source in self.sources:
            try:
                response = requests.get(source, timeout=10)
                if response.status_code == 200:
                    lines = response.text.strip().split('\n')
                    for line in lines:
                        if ':' in line:
                            found_proxies.add(line.strip())
            except Exception as e:
                self.logger.warning(f"Failed to fetch from {source}: {e}")
        
        self.proxies = list(found_proxies)
        self.logger.info(f"Fetched {len(self.proxies)} unique proxies")
        random.shuffle(self.proxies)

    def get_next_proxy(self) -> Optional[str]:
        """Get the next proxy in the list."""
        if not self.proxies:
            self.fetch_proxies()
        
        if not self.proxies:
            return None
            
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return f"http://{proxy}"

    def remove_proxy(self, proxy_url: str):
        """Remove a bad proxy from the list."""
        # proxy_url format: http://ip:port
        raw_proxy = proxy_url.replace("http://", "")
        if raw_proxy in self.proxies:
            self.proxies.remove(raw_proxy)
            self.logger.info(f"Removed bad proxy: {raw_proxy}")
