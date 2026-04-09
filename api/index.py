"""
Vercel entry point for PanaLogis Flask app.

This file is the serverless handler for Vercel deployments.
It resolves all paths relative to the project root so Flask
can find templates, static files, and routes correctly.
"""
import os
import sys

# Resolve project root (one level up from api/)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Change working directory so Flask finds templates/ and static/
os.chdir(_root)

from app import app  # noqa: E402  (import after path setup)

# Vercel's Python runtime looks for a variable named `app` or `handler`
handler = app
