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
        # 1. Check Vercel matched path header
        matched_path = (
            environ.get('HTTP_X_MATCHED_PATH')
            or environ.get('x-matched-path')
            or environ.get('HTTP_X_NOW_ROUTE_MATCHES')
        )
        if matched_path:
            path_only = matched_path.split('?')[0]
            environ['PATH_INFO'] = path_only
        else:
            # 2. Check query string for ?path=
            qs = environ.get('QUERY_STRING', '')
            if 'path=' in qs:
                try:
                    params = parse_qs(qs, keep_blank_values=True)
                    if 'path' in params:
                        req_path = params.pop('path')[0]
                        environ['PATH_INFO'] = '/' + req_path.lstrip('/')
                        environ['QUERY_STRING'] = urlencode(params, doseq=True)
                except Exception:
                    pass

        # 3. Fallback: if PATH_INFO still points to the function itself or empty, map to root
        path_info = environ.get('PATH_INFO', '')
        if path_info in ('/api/index', '/api/index.py', '/api', ''):
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
