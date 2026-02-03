# Codebase Structure

**Analysis Date:** 2026-02-03

## Directory Layout

```
houstontruckwreck-3/
├── app.py                    # Flask application, routes, scheduler setup
├── main.py                   # Entry point for local/Replit execution
├── wsgi.py                   # Entry point for production WSGI servers (Gunicorn)
├── config.py                 # Centralized configuration management
├── models.py                 # SQLite database and ORM-like model classes
├── scraper.py                # TranStar incident scraping logic
├── email_service.py          # SMTP email sending and HTML generation
├── requirements.txt          # Python dependencies
├── database.db               # SQLite database file (generated at runtime)
├── .env                      # Environment variables (secrets, credentials)
├── .env.example              # Template for .env configuration
├── templates/                # Jinja2 HTML templates for Flask routes
│   ├── base.html             # Base template with navigation and styling
│   ├── login.html            # Admin login page
│   ├── dashboard.html        # Main admin dashboard
│   ├── subscribers.html      # Subscriber management interface
│   ├── hazmat_subscribers.html # Hazmat subscriber management
│   ├── settings.html         # Application settings (include_stalls toggle)
│   ├── 404.html              # Not found error page
│   └── 500.html              # Server error page
├── improved_scraper.py       # Alternative scraper implementation (legacy)
├── selenium_scraper.py       # Selenium-based scraper (legacy/unused)
├── test_*.py                 # Test files
├── Procfile                  # Heroku/Render deployment configuration
├── render.yaml               # Render platform deployment config
├── replit.nix                # Replit environment definition
├── truckwreck.png            # Logo image (embedded in emails)
└── .planning/
    └── codebase/             # Planning and analysis documents
```

## Directory Purposes

**Root Directory:**
- Purpose: Entry points, configuration, main application modules
- Contains: Python source files, config, database, environment files
- Key files: `app.py`, `config.py`, `models.py`, `requirements.txt`

**`templates/`:**
- Purpose: Jinja2 HTML templates rendered by Flask routes
- Contains: HTML UI pages with embedded CSS (Bootstrap 5, Font Awesome)
- Key files: `base.html` (shared layout), `dashboard.html` (primary interface)

**`.planning/codebase/`:**
- Purpose: Generated analysis documents for code navigation and understanding
- Contains: ARCHITECTURE.md, STRUCTURE.md, and future analysis docs
- Not committed to initial repo (created during `/gsd:map-codebase` execution)

## Key File Locations

**Entry Points:**

- `main.py` (29 lines): Local/Replit development server bootstrap
  - Reads PORT from environment, runs Flask on `0.0.0.0:{PORT}`
  - Imports and runs `app` from `app.py`

- `wsgi.py` (57 lines): Production WSGI entry point for Gunicorn
  - Validates database directory writability
  - Exports `app` variable for WSGI servers
  - Detects Render platform and adjusts database path to `/tmp/database.db`

**Core Application:**

- `app.py` (501 lines): Flask application factory and HTTP handlers
  - Initializes Flask, Flask-Login, APScheduler
  - Defines 15+ route handlers for web UI and admin functions
  - Manages background scheduler for periodic scraping

- `config.py` (35 lines): Environment-based configuration
  - Database path, email settings, scraping interval, alert thresholds
  - Supports Render platform detection

**Data Layer:**

- `models.py` (440 lines): SQLite abstraction and entity models
  - `Database` class: Connection pooling, table initialization
  - Entity classes: `Incident`, `Subscriber`, `HazmatSubscriber`, `AdminUser`, `SentAlert`, `Settings`
  - CRUD operations: Static methods for queries and updates

**Business Logic:**

- `scraper.py` (490 lines): TranStar incident detection
  - `TranStarScraper` class: API endpoint scraping, HTML fallback
  - Keyword/regex filters for truck and hazmat incidents
  - Deduplication and relevance checking

- `email_service.py` (1124 lines): SMTP email generation and sending
  - `EmailService` class: HTML email templates, test emails, daily summaries
  - Separate alert types: regular (all subscribers) and hazmat-only
  - Logo embedding, Google Maps link generation

**Configuration Files:**

- `.env`: Runtime environment variables (Gmail credentials, API keys, admin password)
- `.env.example`: Template showing required env vars
- `requirements.txt`: Python dependencies (Flask, APScheduler, BeautifulSoup4, etc.)

**Templates:**

- `templates/base.html`: Shared layout with navigation sidebar, CSS variables, responsive grid
- `templates/dashboard.html`: Incident list, subscriber stats, scheduler status, manual controls
- `templates/subscribers.html`: Add/remove/toggle regular subscribers
- `templates/hazmat_subscribers.html`: Add/remove/toggle hazmat subscribers
- `templates/settings.html`: Toggle stall inclusion, view configuration
- `templates/login.html`: Admin authentication form

**Database:**

- `database.db`: SQLite database (auto-generated on first run)
  - Tables: `incidents`, `subscribers`, `hazmat_subscribers`, `sent_alerts`, `admin_users`, `settings`
  - Location: Project root (local) or `/tmp/database.db` (Render production)

## Naming Conventions

**Files:**

- Entry points: lowercase with underscores (`main.py`, `wsgi.py`)
- Application modules: lowercase with underscores (`app.py`, `config.py`, `models.py`, `scraper.py`, `email_service.py`)
- Test files: `test_*.py` pattern (e.g., `test_improvements.py`, `test_system.py`)
- Legacy/alt implementations: `{name}_scraper.py` (e.g., `selenium_scraper.py`, `improved_scraper.py`)

**Directories:**

- Jinja2 templates: `templates/` (Flask convention)
- Analysis documents: `.planning/codebase/` (planning subdirectory)
- Dynamic files: Root level (database.db, .env)

**Python Code:**

- Classes: PascalCase (`Database`, `TranStarScraper`, `EmailService`, `Incident`, `Subscriber`)
- Functions: snake_case (`add_scrape_log()`, `scheduled_scrape()`, `is_relevant_incident()`)
- Constants: UPPER_SNAKE_CASE (Config class attributes: `SECRET_KEY`, `DATABASE_PATH`, `SCRAPE_INTERVAL`)
- Route handlers: snake_case matching URL paths (`def index()`, `def dashboard()`, `def add_subscriber()`)

## Where to Add New Code

**New Feature (e.g., incident severity classification):**
- Primary code: `scraper.py` (scraper logic) and `models.py` (Incident class enhancements)
- Tests: Create `test_severity_classification.py` in root
- If requires database schema change: Modify `Database.init_db()` in `models.py`

**New Admin Page (e.g., incident history viewer):**
- Route handler: Add `@app.route()` function in `app.py`
- Template: Create `templates/incident_history.html` using `base.html` inheritance
- Logic: Add query method to `Incident` class in `models.py`
- Navigation: Update `templates/base.html` sidebar links

**New Alert Type (e.g., noise complaints):**
- Model: Add `NoiseSubscriber` class in `models.py` following `Subscriber`/`HazmatSubscriber` pattern
- Database: Add table creation in `Database.init_db()`
- Routes: Add `/noise_subscribers`, `/add_noise_subscriber`, etc. in `app.py`
- Email: Add `send_noise_alert()` method in `EmailService`

**New Scraper Strategy (e.g., alternative data source):**
- Class: Create new scraper class in `scraper.py` (e.g., `GoogleMapsTrafficScraper`)
- Inheritance: Consider extracting common interface
- Integration: Modify `scheduled_scrape()` in `app.py` to call multiple scrapers

**Utility Functions (e.g., time formatting helper):**
- Location: Add to existing module (e.g., timezone utilities in `config.py`)
- If reusable across modules: Consider adding to `models.py` or creating `utils.py`

## Special Directories

**`templates/`:**
- Purpose: Jinja2 templates for HTML rendering
- Generated: No (manually maintained)
- Committed: Yes (version controlled)

**Root (project root):**
- Purpose: Entry points and configuration
- Generated: `database.db` (auto-created on first run)
- Committed: No for `database.db` and `.env` (added to .gitignore)

## Database Schema Reference

**incidents table:**
```sql
CREATE TABLE incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_hash TEXT UNIQUE NOT NULL,     -- MD5 hash for deduplication
    location TEXT NOT NULL,
    description TEXT NOT NULL,
    incident_time TEXT,                     -- Central Time formatted
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    severity INTEGER DEFAULT 1
)
```

**subscribers table:**
```sql
CREATE TABLE subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**admin_users table:**
```sql
CREATE TABLE admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,            -- Werkzeug hashed password
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**settings table:**
```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,       -- e.g., 'include_stalls'
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Configuration Management

**Environment Variables (from `.env`):**
- `SECRET_KEY`: Flask session encryption key
- `EMAIL_USERNAME`: Gmail account for sending alerts
- `EMAIL_PASSWORD`: Gmail app password (2FA workaround)
- `EMAIL_FROM`: Sender email address (defaults to EMAIL_USERNAME)
- `ADMIN_USERNAME`: Dashboard admin login username
- `ADMIN_PASSWORD`: Dashboard admin login password
- `SCRAPE_INTERVAL`: Seconds between TranStar polls (default: 60)
- `MAX_ALERTS_PER_HOUR`: Rate limit for alerts (default: 20)
- `INCLUDE_STALLS`: Include truck stall incidents in alerts (default: 'true')
- `RENDER`: Set by Render platform; triggers `/tmp/database.db` path
- `PORT`: HTTP server port (default: 5000)
- `REPL_SLUG`, `REPL_OWNER`: Replit-specific environment info

**Platform-Specific:**
- **Local Development:** `database.db` in project root
- **Render Production:** `/tmp/database.db` (ephemeral, rebuilds on deploy)
- **Replit:** `database.db` in project root (persistent filesystem)

---

*Structure analysis: 2026-02-03*
