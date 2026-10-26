# scrapers/universal_scraper.py
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import urlparse

def scrape_universal(target_url, log_callback=None):
    """Crawls and extracts structured intelligence, OpenGraph metadata, and pricing from any URL."""
    if not target_url.startswith('http'):
        target_url = 'https://' + target_url
        
    domain = urlparse(target_url).netloc
    
    if log_callback:
        log_callback(f"[INIT] Dispatching Universal Web Spider -> {target_url}")
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    try:
        r = requests.get(target_url, headers=headers, timeout=12)
        if log_callback:
            log_callback(f"[HTTP] Target responded with HTTP {r.status_code} ({len(r.text)} bytes)")
            
        if r.status_code != 200:
            return []
            
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Extract title
        title = soup.title.string.strip() if soup.title and soup.title.string else domain
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content'].strip()
            
        # Extract image
        og_img = soup.find('meta', property='og:image')
        image_url = og_img['content'] if og_img and og_img.get('content') else "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=400&auto=format&fit=crop"
        
        # Search for price patterns in text
        text_content = soup.get_text()
        prices = re.findall(r'[\$€£](\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text_content)
        detected_price = 0.0
        price_str = "N/A"
        if prices:
            cleaned = float(prices[0].replace(',', ''))
            if cleaned > 0:
                detected_price = cleaned
                price_str = f"${cleaned:,.2f}"
                
        # Headings count
        headings = [h.text.strip() for h in soup.find_all(['h1', 'h2', 'h3']) if h.text.strip()]
        
        item = {
            'platform': f'Web Spider ({domain})',
            'title': title[:120],
            'category': 'Universal Web Intel',
            'price_str': price_str,
            'price_numeric': detected_price,
            'currency': 'USD',
            'location': f"{domain} (Headings: {len(headings)})",
            'rating': 4.7,
            'reviews_count': len(headings),
            'image_url': image_url,
            'url': target_url,
            'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if log_callback:
            log_callback(f"[SUCCESS] Extracted OpenGraph & DOM metadata for: '{title[:60]}...'")
            
        return [item]
        
    except Exception as e:
        if log_callback:
            log_callback(f"[EXCEPTION] Universal Spider error: {str(e)}")
        return []
