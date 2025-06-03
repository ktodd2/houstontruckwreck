import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Use /data directory for database in production (Render disk mount)
    if os.environ.get('RENDER'):
        DATABASE_PATH = '/data/database.db'
    else:
        DATABASE_PATH = 'database.db'
    
    # Email configuration
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    EMAIL_FROM = os.environ.get('EMAIL_FROM') or os.environ.get('EMAIL_USERNAME')
    
    # Scraping configuration
    SCRAPE_INTERVAL = int(os.environ.get('SCRAPE_INTERVAL', 60))  # seconds
    TRANSTAR_URL = 'https://traffic.houstontranstar.org/roadclosures/#all'
    
    # Alert configuration
    MAX_ALERTS_PER_HOUR = int(os.environ.get('MAX_ALERTS_PER_HOUR', 20))
    
    # Admin configuration
    DEFAULT_ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    DEFAULT_ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # Alert filtering configuration
    INCLUDE_STALLS = os.environ.get('INCLUDE_STALLS', 'true').lower() == 'true'
