# External Integrations

**Analysis Date:** 2026-02-03

## APIs & External Services

**TranStar Houston Traffic API:**
- Service: Houston TranStar traffic incident data
- What it's used for: Scrape real-time road closures, accidents, and hazmat incidents
- Base URL: `https://traffic.houstontranstar.org`
- API endpoints: `/api/incidents/freeway`, `/api/incidents/stalls`, `/api/incidents/street`, `/api/incidents/closures`
- Client: requests library (HTTP GET requests)
- User-Agent: Spoofed Chrome browser headers to avoid blocking
- Implementation files: `scraper.py` (TranStarScraper class), `improved_scraper.py`, `selenium_scraper.py`

**Google Maps API:**
- Service: Map link generation for incident locations
- What it's used for: Create clickable Google Maps search links in email alerts
- Usage: URL construction with query parameters (no API key required for search links)
- Implementation: `email_service.py` lines 85-88 (construct maps links)

## Data Storage

**Databases:**
- SQLite 3 (local file-based)
  - Connection: Direct via sqlite3 module, no ORM
  - Client: Built-in sqlite3 (Python standard library)
  - File path:
    - Development: `database.db` (project root)
    - Production (Render): `/tmp/database.db`
  - Tables created in: `models.py` Database class

**File Storage:**
- Local filesystem only
  - Logo image: `truckwreck.png` (encoded as base64 in emails)
  - Database file: SQLite file on disk
  - No cloud storage (S3, GCS, etc.)

**Caching:**
- None - no Redis, Memcached, or other caching layer

## Authentication & Identity

**Auth Provider:**
- Custom built-in authentication
  - Implementation: `models.py` AdminUser class
  - Flask-Login for session management
  - Passwords: Werkzeug generate_password_hash for hashing

**Web Dashboard Login:**
- Single admin user per deployment
- Credentials: Configured via `ADMIN_USERNAME` and `ADMIN_PASSWORD` environment variables
- Default credentials in code: admin / admin123 (must override in production)

## Email & Notifications

**SMTP Provider:**
- Gmail SMTP (smtp.gmail.com:587)
  - Email host: `smtp.gmail.com`
  - Port: 587 (TLS)
  - Authentication: Requires Gmail account + app password (not regular password)
  - Configuration: `config.py` EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD
  - Environment variables:
    - `EMAIL_USERNAME` - Gmail email address
    - `EMAIL_PASSWORD` - Gmail app-specific password
    - `EMAIL_FROM` - Reply-to address

**Email Service Implementation:**
- File: `email_service.py`
- Classes: EmailService with methods for different alert types
- Recipient lists: Stored in SQLite tables
  - `subscribers` - Regular incident alerts
  - `hazmat_subscribers` - Hazmat/spill-only alerts
- Email types generated:
  - Regular incident alerts (send_alert method)
  - Hazmat-specific alerts (send_hazmat_alert method)
  - Test emails (send_test_email method)
  - Daily summary emails (send_daily_summary method)
- Email format: HTML+text multipart MIME messages with embedded logo image (base64)

## Monitoring & Observability

**Error Tracking:**
- None - No Sentry, Rollbar, or similar service

**Logs:**
- File: stdout/stderr via Python logging module (basicConfig at logging.INFO level)
- In-memory buffer: Circular deque in app.py (scrape_logs, maxlen=100) for dashboard display
- Logging is visible in: Render.com logs, Replit console, or gunicorn stderr

## CI/CD & Deployment

**Hosting:**
- Primary: Render.com (Web service, Python environment)
- Alternative: Replit platform
- Local: Development machines via Flask dev server or gunicorn

**CI Pipeline:**
- None detected - No GitHub Actions, GitLab CI, or similar
- Manual deployment via Render.com dashboard or git push to Render

**Deployment Configuration:**
- `render.yaml` - Render.com service configuration
  - buildCommand: `pip install -r requirements.txt`
  - startCommand: `gunicorn wsgi:app`
- `Procfile` - Heroku-compatible format
- Environment variables set in Render dashboard

## Environment Configuration

**Required env vars for email:**
- `EMAIL_USERNAME` - Gmail address
- `EMAIL_PASSWORD` - Gmail app password (critical - must be app password, not account password)
- `EMAIL_FROM` - Sender address
- `SECRET_KEY` - Flask session key (auto-generated in Render)

**Optional env vars:**
- `SCRAPE_INTERVAL` - Scrape frequency in seconds (default 60)
- `MAX_ALERTS_PER_HOUR` - Alert rate limit (default 20)
- `ADMIN_USERNAME` - Dashboard admin username (default: admin)
- `ADMIN_PASSWORD` - Dashboard admin password (default: admin123)
- `INCLUDE_STALLS` - Include vehicle stalls in alerts (default: true)
- `PORT` - HTTP port (default 5000)

**Secrets location:**
- Development: `.env` file (git-ignored)
- Production (Render): Environment variables set in Render dashboard
- `.env.example` - Template file showing required variables

## Webhooks & Callbacks

**Incoming:**
- None - Application does not expose webhook endpoints

**Outgoing:**
- Email notifications to subscribers (send_alert, send_hazmat_alert methods)
- No webhooks to external services

## Third-party Services Summary

- **External APIs:** TranStar Houston (web scraping), Google Maps (link generation)
- **Email:** Gmail SMTP (requires active Gmail account with app password)
- **Hosting:** Render.com
- **Authentication:** Custom in-memory admin auth
- **Database:** SQLite (local file, no managed service)

---

*Integration audit: 2026-02-03*
