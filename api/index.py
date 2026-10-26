# api/index.py
import sys
import os

# Set VERCEL environment flag
os.environ['VERCEL'] = '1'

# Add root directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app
import db_manager

# Expose WSGI callables
handler = app
