#!/usr/bin/env python3
"""
Houston Traffic Monitor - Replit Entry Point
Main entry point for running on Replit platform
"""

import os
import sys
from app import app

if __name__ == '__main__':
    # Replit-specific configuration
    host = '0.0.0.0'
    port = int(os.environ.get('PORT', 5000))
    
    print("🚛 Houston Traffic Monitor Starting on Replit...")
    print(f"📊 Dashboard will be available at: https://{os.environ.get('REPL_SLUG', 'your-repl')}.{os.environ.get('REPL_OWNER', 'username')}.repl.co")
    print(f"👤 Default admin login: admin / admin123")
    print(f"⏱️  Scraping interval: 60 seconds")
    print(f"📧 Email configured: {bool(os.environ.get('EMAIL_USERNAME') and os.environ.get('EMAIL_PASSWORD'))}")
    print("🔧 Configure your email settings in the Secrets tab!")
    
    # Run the Flask app
    app.run(
        host=host,
        port=port,
        debug=False,  # Disable debug mode in production
        threaded=True
    )
