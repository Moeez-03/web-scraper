# api/index.py
import sys
import os
from urllib.parse import parse_qs, urlencode

# Set VERCEL environment flag
os.environ['VERCEL'] = '1'

# Add root directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app
import db_manager

# WSGI Middleware to restore original PATH_INFO from Vercel rewrite
class VercelPathFixMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        qs = environ.get('QUERY_STRING', '')
        if '__vercel_path=' in qs:
            try:
                params = parse_qs(qs, keep_blank_values=True)
                if '__vercel_path' in params:
                    raw_path = params.pop('__vercel_path')[0]
                    clean_path = '/' + raw_path.lstrip('/')
                    environ['PATH_INFO'] = clean_path
                    environ['QUERY_STRING'] = urlencode(params, doseq=True)
            except Exception as e:
                print(f"[!] Path rewrite error: {e}", file=sys.stderr)
        elif environ.get('PATH_INFO') in ('/api/index', '/api/index.py', '/api', ''):
            environ['PATH_INFO'] = '/'

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

# Initialize DB on cold start
try:
    db_manager.init_db()
except Exception as e:
    print(f"[!] DB init notice: {e}", file=sys.stderr)

# Expose WSGI callable
handler = app
