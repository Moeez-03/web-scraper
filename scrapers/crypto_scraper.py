# scrapers/crypto_scraper.py
import requests
from datetime import datetime

def scrape_crypto(limit=25, log_callback=None):
    """Fetches real-time financial cryptocurrency and digital asset price intelligence."""
    if log_callback:
        log_callback(f"[INIT] Connecting to Global Decentralized Market Telemetry Feed...")
        
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        
        if log_callback:
            log_callback(f"[HTTP] Financial API responded with status {r.status_code}")
            
        if r.status_code != 200:
            return []
            
        data = r.json()
        extracted = []
        for coin in data[:limit]:
            price_val = float(coin.get('current_price', 0))
            change_24h = float(coin.get('price_change_percentage_24h') or 0.0)
            change_str = f"+{change_24h:.2f}%" if change_24h >= 0 else f"{change_24h:.2f}%"
            
            item = {
                'platform': 'CoinGecko / Market Ticker',
                'title': f"{coin.get('name')} ({coin.get('symbol', '').upper()}) — 24h: {change_str}",
                'category': 'Crypto & Financials',
                'price_str': f"${price_val:,.2f}" if price_val >= 1 else f"${price_val:.4f}",
                'price_numeric': price_val,
                'currency': 'USD',
                'location': f"Market Cap: ${coin.get('market_cap', 0):,.0f}",
                'rating': round(4.0 + (5.0 if change_24h > 0 else 3.5) / 2, 1),
                'reviews_count': int((coin.get('total_volume', 1000) % 5000) / 10 + 50),
                'image_url': coin.get('image') or "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?q=80&w=400&auto=format&fit=crop",
                'url': f"https://www.coingecko.com/en/coins/{coin.get('id', '')}",
                'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            extracted.append(item)
            
        if log_callback:
            log_callback(f"[SUCCESS] Ingested {len(extracted)} real-time market tickers into DataOps pipeline")
            
        return extracted
        
    except Exception as e:
        if log_callback:
            log_callback(f"[EXCEPTION] Financial Market crawler error: {str(e)}")
        return []
