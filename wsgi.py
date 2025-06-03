"""
Houston Traffic Monitor - WSGI Entry Point
Main entry point for running on production servers with Gunicorn
"""

import os
import sys
from app import app
from config import Config

# Print startup information
print("🚛 Houston Traffic Monitor Starting in Production...")
print(f"📊 Dashboard will be available at the configured URL")
print(f"👤 Default admin login: {os.environ.get('ADMIN_USERNAME', 'admin')}")
print(f"⏱️  Scraping interval: {os.environ.get('SCRAPE_INTERVAL', '60')} seconds")
print(f"📧 Email configured: {bool(os.environ.get('EMAIL_USERNAME') and os.environ.get('EMAIL_PASSWORD'))}")

# Print database information
print(f"💾 Database path: {Config.DATABASE_PATH}")
db_dir = os.path.dirname(Config.DATABASE_PATH)
if db_dir:
    print(f"📁 Database directory: {db_dir}")
    if os.path.exists(db_dir):
        print(f"✅ Database directory exists")
        # Check if directory is writable
        try:
            test_file = os.path.join(db_dir, 'test_write.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print(f"✅ Database directory is writable")
        except Exception as e:
            print(f"❌ Database directory is not writable: {e}")
    else:
        print(f"❌ Database directory does not exist")
        try:
            os.makedirs(db_dir, exist_ok=True)
            print(f"✅ Created database directory")
        except Exception as e:
            print(f"❌ Failed to create database directory: {e}")

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
