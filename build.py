#!/usr/bin/env python3
"""
Vercel Build Script
Packages the Flask app into a standalone serverless function.
"""
import os
import shutil
import sys

# Install Flask and dependencies for the build
os.system('pip install flask gunicorn')

# The api/index.py will be the serverless handler
print("Build complete!")