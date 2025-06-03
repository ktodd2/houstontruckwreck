"""
Houston Traffic Monitor - WSGI Entry Point
Main entry point for running on production servers with Gunicorn
"""

import os
from app import app

# Print startup information
print("🚛 Houston Traffic Monitor Starting in Production...")
print(f"📊 Dashboard will be available at the configured URL")
print(f"👤 Default admin login: {os.environ.get('ADMIN_USERNAME', 'admin')}")
print(f"⏱️  Scraping interval: {os.environ.get('SCRAPE_INTERVAL', '60')} seconds")
print(f"📧 Email configured: {bool(os.environ.get('EMAIL_USERNAME') and os.environ.get('EMAIL_PASSWORD'))}")

# This app variable is used by Gunicorn
# The app is imported from app.py

if __name__ == '__main__':
    # Production configuration for direct execution
    host = '0.0.0.0'
    port = int(os.environ.get('PORT', 5000))
    
    # Run the Flask app
    app.run(
        host=host,
        port=port,
        debug=False,  # Disable debug mode in production
        threaded=True
    )
