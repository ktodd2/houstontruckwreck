# Technology Stack

**Analysis Date:** 2026-02-03

## Languages

**Primary:**
- Python 3.10 - Backend web application, data scraping, email services

## Runtime

**Environment:**
- Python 3.10 (via Replit/Nix)

**Package Manager:**
- pip
- Lockfile: requirements.txt (pinned versions)

## Frameworks

**Core:**
- Flask 2.3.3 - Web framework for HTTP routes and template rendering
- Flask-Login 0.6.3 - Authentication and session management

**Task Scheduling:**
- APScheduler 3.10.4 - Background job scheduling for periodic scraping and email tasks

**Web Server:**
- Gunicorn 21.2.0 - Production WSGI HTTP server
- Werkzeug 2.3.7 - WSGI utilities and request handling

## Key Dependencies

**Critical:**
- requests 2.31.0 - HTTP client for scraping TranStar API
- beautifulsoup4 4.12.2 - HTML parsing for incident data extraction
- pytz 2023.3 - Timezone handling (Central Time for Houston)
- python-dotenv 1.0.0 - Environment variable configuration loading
- email-validator 2.0.0 - Email address validation for subscribers

**Standard Library Usage:**
- sqlite3 - Built-in database (local file-based SQLite)
- smtplib - Built-in SMTP client for email sending
- email.mime - Built-in email message construction
- logging - Built-in application logging
- json, re, urllib - Standard utilities

## Configuration

**Environment:**
- Configuration loaded via `config.py` which reads `.env` file using python-dotenv
- Key environment variables:
  - `EMAIL_USERNAME` - Gmail account for SMTP authentication
  - `EMAIL_PASSWORD` - Gmail app password for SMTP
  - `EMAIL_FROM` - Reply-to address for outbound emails
  - `SECRET_KEY` - Flask session signing key
  - `SCRAPE_INTERVAL` - Seconds between incident scrape cycles (default: 60)
  - `MAX_ALERTS_PER_HOUR` - Rate limiting for alerts (default: 20)
  - `ADMIN_USERNAME` - Web dashboard admin login (default: admin)
  - `ADMIN_PASSWORD` - Web dashboard admin password
  - `INCLUDE_STALLS` - Include vehicle stall incidents in alerts (default: true)
  - `RENDER` - Platform identifier for conditional database path

**Build:**
- `Procfile` - Procfile format: `web: gunicorn wsgi:app`
- `render.yaml` - Render.com deployment config with buildCommand: `pip install -r requirements.txt`
- `replit.nix` - Nix environment for Replit platform with Python 3.10

## Database

**Type:** SQLite 3
- File-based relational database
- Default location: `database.db` (project root) or `/tmp/database.db` (production/Render)
- Tables: incidents, subscribers, hazmat_subscribers, sent_alerts, admin_users, settings
- No ORM used - direct sqlite3 connection with SQL queries

## Platform Requirements

**Development:**
- Python 3.10
- pip package manager
- Runs on: Replit, local development, Render.com

**Production:**
- Deployment target: Render.com (Web service with Python 3.x environment)
- Alternative: Any WSGI-capable host (via gunicorn)
- Database: SQLite with writable filesystem or `/tmp` directory

---

*Stack analysis: 2026-02-03*
