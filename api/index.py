#!/usr/bin/env python3
# api/index.py — Vercel Python serverless entry point
import sys
import os

# Add project root to path so "from app import app" works
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app as application

# Vercel Python runtime looks for "app" or "handler"
app = application