# d:/desktop3/web-scraper/app.py
import os
import sys
import json
import time
import queue
import threading
from io import BytesIO, StringIO
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_file
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db_manager
from scrapers.craigslist_scraper import scrape_craigslist
from scrapers.ecommerce_scraper import scrape_ecommerce
from scrapers.crypto_scraper import scrape_crypto
from scrapers.universal_scraper import scrape_universal

_base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=os.path.join(_base_dir, 'static'),
    template_folder=os.path.join(_base_dir, 'templates')
)

# Initialize DB on start
db_manager.init_db()

# Global log queue for real-time crawler streaming
log_subscribers = []
active_job = {
    'running': False,
    'platform': None,
    'query': None,
    'progress': 0,
    'status': 'Idle'
}

def broadcast_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{ts}] {msg}"
    print(formatted)
    for q in list(log_subscribers):
        try:
            q.put_nowait(formatted)
        except:
            pass

@app.route('/')
@app.route('/api/index')
def dashboard():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM intel_records")
    total_records = c.fetchone()[0]
    
    c.execute("SELECT AVG(price_numeric), MAX(price_numeric) FROM intel_records WHERE price_numeric > 0")
    row = c.fetchone()
    avg_price = round(row[0] or 0)
    max_price = round(row[1] or 0)
    
    c.execute("SELECT COUNT(DISTINCT platform) FROM intel_records")
    total_platforms = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT category) FROM intel_records")
    total_categories = c.fetchone()[0]
    
    # Recent platform counts
    c.execute("SELECT platform, COUNT(*) as cnt FROM intel_records GROUP BY platform ORDER BY cnt DESC")
    platform_counts = {r['platform']: r['cnt'] for r in c.fetchall()}
    
    conn.close()
    
    return jsonify({
        'total_records': f"{total_records:,}",
        'avg_price': f"${avg_price:,.0f}",
        'max_price': f"${max_price:,.0f}",
        'total_platforms': total_platforms,
        'total_categories': total_categories,
        'platform_counts': platform_counts,
        'active_job': active_job
    })

@app.route('/api/records')
def api_records():
    query = request.args.get('q', '').strip()
    platform = request.args.get('platform', 'all').strip()
    category = request.args.get('category', 'all').strip()
    sort_by = request.args.get('sort', 'newest')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    sql = "SELECT * FROM intel_records WHERE 1=1"
    params = []
    
    if query:
        sql += " AND (title LIKE ? OR location LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])
        
    if platform != 'all':
        sql += " AND platform = ?"
        params.append(platform)
        
    if category != 'all':
        sql += " AND category = ?"
        params.append(category)
        
    if sort_by == 'price_asc':
        sql += " AND price_numeric > 0 ORDER BY price_numeric ASC"
    elif sort_by == 'price_desc':
        sql += " ORDER BY price_numeric DESC"
    elif sort_by == 'rating_desc':
        sql += " ORDER BY rating DESC"
    else:
        sql += " ORDER BY id DESC"
        
    sql += f" LIMIT {limit} OFFSET {offset}"
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute(sql, params)
    rows = [dict(r) for r in c.fetchall()]
    
    # Total count matching
    count_sql = "SELECT COUNT(*) FROM intel_records WHERE 1=1"
    c.execute(count_sql)
    total_match = c.fetchone()[0]
    conn.close()
    
    return jsonify({
        'records': rows,
        'total': total_match,
        'count': len(rows)
    })

@app.route('/api/charts/data')
def api_charts_data():
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    # 1. Platform Distribution & Avg Price
    c.execute("""
        SELECT platform, COUNT(*) as cnt, AVG(price_numeric) as avg_p
        FROM intel_records
        GROUP BY platform
        ORDER BY cnt DESC
    """)
    platforms = []
    platform_counts = []
    platform_avg_prices = []
    for r in c.fetchall():
        platforms.append(r['platform'])
        platform_counts.append(r['cnt'])
        platform_avg_prices.append(round(r['avg_p'] or 0))
        
    # 2. Category Distribution
    c.execute("""
        SELECT category, COUNT(*) as cnt
        FROM intel_records
        GROUP BY category
        ORDER BY cnt DESC
        LIMIT 7
    """)
    categories = []
    category_counts = []
    for r in c.fetchall():
        categories.append(r['category'])
        category_counts.append(r['cnt'])
        
    # 3. Top Valued Items (Luxury / Commercial)
    c.execute("""
        SELECT title, price_numeric, platform, category
        FROM intel_records
        WHERE price_numeric > 0 AND title != 'No Title' AND title != 'Untitled' AND title IS NOT NULL
        ORDER BY price_numeric DESC
        LIMIT 6
    """)
    top_assets = []
    for r in c.fetchall():
        name = r['title'] if r['title'] and r['title'] != 'No Title' else f"Asset ({r['category']})"
        t = name[:26] + '...' if len(name) > 26 else name
        top_assets.append({
            'name': t,
            'price': round(r['price_numeric']),
            'platform': r['platform']
        })
        
    # 4. Price Bracket Distribution
    c.execute("""
        SELECT 
            SUM(CASE WHEN price_numeric < 50 THEN 1 ELSE 0 END) as b1,
            SUM(CASE WHEN price_numeric >= 50 AND price_numeric < 250 THEN 1 ELSE 0 END) as b2,
            SUM(CASE WHEN price_numeric >= 250 AND price_numeric < 1000 THEN 1 ELSE 0 END) as b3,
            SUM(CASE WHEN price_numeric >= 1000 AND price_numeric < 5000 THEN 1 ELSE 0 END) as b4,
            SUM(CASE WHEN price_numeric >= 5000 AND price_numeric < 50000 THEN 1 ELSE 0 END) as b5,
            SUM(CASE WHEN price_numeric >= 50000 THEN 1 ELSE 0 END) as b6
        FROM intel_records WHERE price_numeric > 0
    """)
    row = c.fetchone()
    price_brackets = [
        {'label': '< $50', 'count': row['b1'] or 0},
        {'label': '$50 - $250', 'count': row['b2'] or 0},
        {'label': '$250 - $1K', 'count': row['b3'] or 0},
        {'label': '$1K - $5K', 'count': row['b4'] or 0},
        {'label': '$5K - $50K', 'count': row['b5'] or 0},
        {'label': '$50K+', 'count': row['b6'] or 0},
    ]
    
    conn.close()
    
    return jsonify({
        'platforms': platforms,
        'platform_counts': platform_counts,
        'platform_avg_prices': platform_avg_prices,
        'categories': categories,
        'category_counts': category_counts,
        'top_assets': top_assets,
        'price_brackets': price_brackets
    })

@app.route('/api/scrape/stream')
def api_scrape_stream():
    """SSE endpoint streaming live crawler logs to the browser terminal."""
    def event_stream():
        q = queue.Queue()
        log_subscribers.append(q)
        q.put(f"[{datetime.now().strftime('%H:%M:%S')}] [CONNECT] Terminal pipe established. MarketPulse Agent v2.5 Online.")
        try:
            while True:
                msg = q.get()
                yield f"data: {json.dumps({'log': msg})}\n\n"
        except GeneratorExit:
            log_subscribers.remove(q)
            
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/api/scrape/start', methods=['POST'])
def api_scrape_start():
    global active_job
    if active_job['running']:
        return jsonify({'error': 'A scraping pipeline is already running in background.'}), 400
        
    data = request.json or {}
    platform = data.get('platform', 'craigslist').lower()
    query = data.get('query', 'laptop').strip()
    city = data.get('city', 'New York').strip()
    limit = int(data.get('limit', 20))
    target_url = data.get('url', '').strip()
    
    def run_pipeline():
        global active_job
        active_job['running'] = True
        active_job['platform'] = platform
        active_job['query'] = query or target_url
        active_job['progress'] = 10
        active_job['status'] = 'Active'
        
        broadcast_log(f"⚡ DISPATCHING PIPELINE -> Platform: {platform.upper()} | Target: {query or target_url}")
        broadcast_log(f"[STEALTH] Rotating TLS fingerprint & user-agent headers...")
        time.sleep(0.5)
        
        records = []
        try:
            if platform == 'craigslist':
                active_job['progress'] = 30
                records = scrape_craigslist(query=query, city=city, max_results=limit, log_callback=broadcast_log)
            elif platform == 'ecommerce':
                active_job['progress'] = 30
                records = scrape_ecommerce(query=query, limit=limit, log_callback=broadcast_log)
            elif platform == 'crypto':
                active_job['progress'] = 30
                records = scrape_crypto(limit=limit, log_callback=broadcast_log)
            elif platform == 'universal':
                active_job['progress'] = 30
                records = scrape_universal(target_url=target_url or 'https://news.ycombinator.com', log_callback=broadcast_log)
            elif platform == 'olx':
                active_job['progress'] = 30
                broadcast_log(f"[OLX] Launching Headless Chrome driver with anti-detection...")
                try:
                    from classified_scrapper import ClassifiedScraper
                    scraper = ClassifiedScraper(site='olx')
                    scraper.run_scraper([query or 'mieszkanie'], max_pages=1, region=city)
                    db_manager.migrate_and_seed(db_manager.get_connection())
                    broadcast_log(f"[OLX] Scraping completed. Database synchronized.")
                except Exception as e:
                    broadcast_log(f"[OLX] Headless browser note: {e}")
                
            active_job['progress'] = 75
            if records:
                broadcast_log(f"[PERSIST] Writing {len(records)} normalized records to SQLite relational cache...")
                inserted = db_manager.insert_records(records)
                broadcast_log(f"[PERSIST] ✅ Successfully committed {inserted} records to database.")
                
            active_job['progress'] = 100
            broadcast_log(f"🎉 PIPELINE COMPLETED SUCCESSFULLY! Telemetry & Charts updated.")
            
        except Exception as e:
            broadcast_log(f"❌ PIPELINE ERROR: {str(e)}")
        finally:
            active_job['running'] = False
            active_job['status'] = 'Idle'

    t = threading.Thread(target=run_pipeline, daemon=True)
    t.start()
    
    return jsonify({'status': 'dispatched', 'platform': platform, 'query': query})

@app.route('/api/export/<fmt>')
def api_export(fmt):
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute("SELECT id, platform, title, category, price_str, price_numeric, currency, location, rating, reviews_count, url, scraped_at FROM intel_records ORDER BY id DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    
    df = pd.DataFrame(rows)
    filename = f"MarketPulse_Intelligence_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if fmt == 'csv':
        buffer = StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return Response(
            buffer.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}.csv'}
        )
    elif fmt == 'json':
        return Response(
            df.to_json(orient='records', indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={filename}.json'}
        )
    elif fmt == 'xlsx':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Intelligence Records', index=False)
            ws = writer.sheets['Intelligence Records']
            # Header styling
            header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='10B981', end_color='10B981', fill_type='solid')
            for col in range(1, len(df.columns) + 1):
                cell = ws.cell(row=1, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 22
        output.seek(0)
        return send_file(
            output,
            download_name=f"{filename}.xlsx",
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    return "Unsupported format", 400

if __name__ == '__main__':
    print("[*] MarketPulse Enterprise Web Intelligence starting at http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False)
