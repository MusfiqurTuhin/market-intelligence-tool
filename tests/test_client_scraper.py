from scrapers.main_scraper_clients import ClientScraper
import os

class TestClientScraper(ClientScraper):
    def __init__(self):
        super().__init__()
        self.input_file = "data/raw/test_partners.csv"
        self.output_file = "data/raw/test_partner_clients.csv"
        # Ensure clean start for test
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
        self.processed_partners = set() # Clear processed partners loaded by parent
        self._init_csv()

if __name__ == "__main__":
    scraper = TestClientScraper()
    # Monkey patch fetch_page to save HTML
    original_fetch = scraper.fetch_page
    def fetch_and_save(url):
        res = original_fetch(url)
        if scraper.page:
            with open("debug_test.html", "w") as f:
                f.write(scraper.page.content())
        return res
    scraper.fetch_page = fetch_and_save
    scraper.scrape()
