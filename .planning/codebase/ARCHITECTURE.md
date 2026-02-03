# Architecture

**Analysis Date:** 2026-02-03

## Pattern Overview

**Overall:** Flask-based monolithic web application with background job scheduling and external scraping integration.

**Key Characteristics:**
- MVC-inspired separation with Flask for web layer, SQLite for data persistence, separate scraper and email service modules
- Background scheduler (APScheduler) for automated incident scraping and daily email summaries
- Authentication layer with Flask-Login for admin access
- Real-time monitoring dashboard with manual trigger capabilities
- Dual subscriber system for general and hazmat-specific alerts

## Layers

**Web Layer:**
- Purpose: Handle HTTP requests, render templates, manage user authentication and interactions
- Location: `app.py` (501 lines - routes and handlers)
- Contains: Flask route handlers, login manager, template rendering
- Depends on: `models.py` (data access), `email_service.py` (alert sending), `scraper.py` (incident detection)
- Used by: Web browsers, authenticated admin users

**Data Layer:**
- Purpose: SQLite database abstraction and CRUD operations for domain entities
- Location: `models.py` (440 lines)
- Contains: `Database` class for connection management, `Incident`, `Subscriber`, `HazmatSubscriber`, `AdminUser`, `Settings`, `SentAlert` model classes
- Depends on: SQLite3 (stdlib), Werkzeug for password hashing
- Used by: All layers for persistence

**Scraper Layer:**
- Purpose: Extract traffic incidents from TranStar API and HTML fallback
- Location: `scraper.py` (490 lines)
- Contains: `TranStarScraper` class for incident detection using keyword matching and regex patterns
- Depends on: `models.py` for incident creation and storage
- Used by: Scheduler (scheduled scrapes), dashboard (manual scrapes)

**Email Service Layer:**
- Purpose: Format and send alert emails to subscribers
- Location: `email_service.py` (1124 lines - largest module)
- Contains: `EmailService` class with HTML email generation, test emails, daily summaries, hazmat-specific alerts
- Depends on: `models.py` for subscriber/incident lookup, SMTPlib for Gmail SMTP
- Used by: Scheduler (background tasks), dashboard (manual test emails)

**Configuration Layer:**
- Purpose: Centralized environment-based configuration
- Location: `config.py` (35 lines)
- Contains: `Config` class with database path, email settings, scraping intervals, alert thresholds
- Depends on: Environment variables (dotenv), platform detection (Render vs local)
- Used by: All layers

## Data Flow

**Scheduled Scraping Cycle (every 60 seconds by default):**

1. APScheduler triggers `scheduled_scrape()` in `app.py`
2. `TranStarScraper.run_scrape_cycle()` fetches incidents via TranStar API endpoints
3. Scraper filters incidents using `is_relevant_incident()` (truck/hazmat keywords + regex)
4. New incidents saved to database via `Incident.save(db)` (deduplication via incident hash)
5. `SentAlert` records created for tracked alerts
6. `EmailService.send_alert(new_incidents)` sends to regular subscribers
7. `EmailService.send_hazmat_alert(new_incidents)` sends to hazmat subscribers only
8. Scrape results logged to in-memory circular buffer (max 100 entries)

**Daily Summary (midnight CST):**

1. APScheduler triggers `send_daily_summary()` at 00:00 America/Chicago timezone
2. `EmailService.send_daily_summary(target_email)` generates report of all incidents from past 24 hours
3. Email sent via SMTP (Gmail)

**Manual Incident Trigger:**

1. Admin user clicks "Manual Scrape" button on dashboard
2. POST to `/manual_scrape` triggers `scraper.run_scrape_cycle()`
3. Same flow as scheduled cycle
4. Results displayed in dashboard with user feedback

**Dashboard Access:**

1. User accesses `/` → redirects to login if not authenticated
2. Credentials validated against `admin_users` table via `AdminUser.authenticate()`
3. On success, session token set, redirect to `/dashboard`
4. Dashboard loads recent incidents, subscriber counts, alert statistics
5. Scheduler status and next run time displayed

**State Management:**

- **In-Memory:** Scrape logs stored in `deque(maxlen=100)` for UI display
- **Persistent:** All incidents, subscribers, alerts stored in SQLite (`database.db`)
- **Transient:** Flask session tokens managed by Flask-Login middleware
- **Configuration:** Settings table stores application flags (e.g., `include_stalls` toggle)

## Key Abstractions

**Incident:**
- Purpose: Represents a traffic incident (truck accident, hazmat spill, etc.)
- Examples: `models.py` class methods include `save()`, `get_recent()`, `is_already_sent()`
- Pattern: Data class with hash-based deduplication (MD5 hash of location + description)
- Lifecycle: Created by scraper → saved to DB → alerts sent → query for dashboard

**TranStarScraper:**
- Purpose: Encapsulate incident detection logic from external source
- Examples: Keyword matching, regex patterns, API endpoint handling
- Pattern: Strategy pattern with API-first, HTML fallback approach
- Filters: Excludes street incidents, stalls (configurable), generic events

**Subscriber Management:**
- Purpose: Track alert recipients with granular filtering
- Examples: `Subscriber` (all alerts) vs `HazmatSubscriber` (hazmat-only)
- Pattern: Separate model classes for different alert preferences
- Attributes: email, active status, creation timestamp

**Settings:**
- Purpose: Persistent application configuration flags
- Examples: `include_stalls` boolean toggle
- Pattern: Key-value store in database, retrieved on scraper initialization

## Entry Points

**Web Server (`main.py`):**
- Location: `main.py` (29 lines)
- Triggers: Executed by user or deployment platform (Replit, Render)
- Responsibilities: Initialize Flask app, bind to `0.0.0.0:{PORT}`, start background scheduler
- Exit pattern: Scheduler shutdown via `atexit` handler

**WSGI Server (`wsgi.py`):**
- Location: `wsgi.py` (57 lines)
- Triggers: Gunicorn/production WSGI servers
- Responsibilities: Validate database directory writability, expose `app` variable for WSGI servers
- Configuration: Reads `RENDER` env var to detect Render platform

**Background Scheduler (in `app.py`):**
- Location: `app.py` lines 118-139
- Triggers: Automatic on application startup via APScheduler
- Jobs:
  - `scheduled_scrape`: IntervalTrigger every 60 seconds (configurable)
  - `send_daily_summary`: CronTrigger at midnight CST daily

## Error Handling

**Strategy:** Try-catch at service layer boundaries; errors logged and surfaced to users via flash messages

**Patterns:**

1. **Database Errors:**
   - SQLite IntegrityError caught during `Incident.save()` (duplicate hash) → silently ignored (new incident not added)
   - Subscriber operations return boolean (True/False) for caller feedback

2. **Email Failures:**
   - SMTP connection errors caught in `EmailService.send_alert()` → logged to console and returns False
   - Web handlers display flash message: "Failed to send email" or similar
   - Dashboard shows alert send success/failure to admin

3. **Scraper Errors:**
   - Network timeouts (requests lib, 15-30s timeout) caught and logged
   - JSON decode errors from API treated as warnings, fallback to HTML scraping
   - Missing API endpoints logged but don't block application

4. **Scheduler Errors:**
   - Exceptions in `scheduled_scrape()` caught and logged via `add_scrape_log(..., 'error')`
   - Scheduler continues running despite errors
   - Error buffer visible in scrape logs UI

## Cross-Cutting Concerns

**Logging:**
- Standard Python logging configured in multiple modules (`logging.basicConfig(level=logging.INFO)`)
- Application logs to console and dashboard scrape log buffer
- No centralized log aggregation; local logs only

**Validation:**
- Email format: Regex pattern `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$` on form input
- Incident relevance: Keyword/regex matching in `TranStarScraper.is_relevant_incident()`
- No input sanitization; potential XSS/SQL injection risks

**Authentication:**
- Flask-Login session-based with user loader from database
- Admin credentials hashed with Werkzeug `generate_password_hash()/check_password_hash()`
- @login_required decorator protects all admin routes

**Timezone:**
- Central Time (America/Chicago) hardcoded throughout for incident times and summaries
- Uses pytz library for timezone-aware datetime operations

---

*Architecture analysis: 2026-02-03*
