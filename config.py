import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Use /tmp directory for database in production (Render)
    if os.environ.get('RENDER'):
        DATABASE_PATH = '/tmp/database.db'
    else:
        # Use a directory that we have permission to access
        DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    
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

    # Telnyx SMS Configuration
    TELNYX_API_KEY = os.environ.get('TELNYX_API_KEY')
    TELNYX_FROM_NUMBER = os.environ.get('TELNYX_FROM_NUMBER')
    SMS_ENABLED = os.environ.get('SMS_ENABLED', 'false').lower() == 'true'
    SMS_MAX_ALERTS_PER_HOUR = int(os.environ.get('SMS_MAX_ALERTS_PER_HOUR', 20))
