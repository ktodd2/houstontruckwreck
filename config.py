import hashlib
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

    # Live wall store feed: the driveshaftcable.com Supabase edge function that
    # returns unfilled orders and sales/profit KPIs. The URL is stable enough to
    # default; the token is a secret and must come from the environment.
    STORE_STATS_URL = os.environ.get(
        'STORE_STATS_URL',
        'https://twrihhyfvomqiqbxkitc.supabase.co/functions/v1/live-wall-stats')
    STORE_STATS_TOKEN = os.environ.get('STORE_STATS_TOKEN')
    STORE_STATS_CACHE_SECONDS = int(os.environ.get('STORE_STATS_CACHE_SECONDS', 30))

    # Token used by external automations (scheduled briefing tasks) to push
    # headline content into the live wall dashboard via POST /api/briefing.
    #
    # Prefer an explicit BRIEFING_TOKEN env var. Otherwise derive a stable
    # token from SECRET_KEY so the endpoint works on an existing deploy with
    # no new configuration — but never derive one from the public default
    # SECRET_KEY, which anyone reading the source could reproduce.
    @staticmethod
    def _resolve_briefing_token():
        explicit = os.environ.get('BRIEFING_TOKEN')
        if explicit:
            return explicit
        secret = os.environ.get('SECRET_KEY')
        if not secret or secret == 'dev-secret-key-change-in-production':
            return None
        return hashlib.sha256(('briefing:' + secret).encode()).hexdigest()[:40]


Config.BRIEFING_TOKEN = Config._resolve_briefing_token()
