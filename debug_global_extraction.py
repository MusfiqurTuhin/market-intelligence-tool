from bs4 import BeautifulSoup

def test_extraction():
    with open('global_partners_page1.html', 'r') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try the current selector
    selector = 'div.col-12.mb-4 > div > a.text-decoration-none'
    cards = soup.select(selector)
    print(f"Selector '{selector}' found {len(cards)} cards")
    
    # Try a broader selector if that fails
    if len(cards) == 0:
        print("Trying broader selectors...")
        # Look for links with /partners/ in href
        links = soup.find_all('a', href=True)
        partner_links = [l for l in links if '/partners/' in l['href'] and 'country' not in l['href'] and 'grade' not in l['href']]
        print(f"Found {len(partner_links)} potential partner links via href filtering")
        for l in partner_links[:3]:
            print(f" - {l['href']}")
            print(f" - Parent classes: {l.parent.get('class')}")
            print(f" - Grandparent classes: {l.parent.parent.get('class')}")

if __name__ == "__main__":
    test_extraction()
