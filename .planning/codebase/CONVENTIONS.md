# Coding Conventions

**Analysis Date:** 2026-02-03

## Naming Patterns

**Files:**
- Lowercase with underscores: `scraper.py`, `email_service.py`, `improved_scraper.py`
- Test files use prefix `test_`: `test_system.py`, `test_incident_detection.py`, `test_improvements.py`

**Functions:**
- Lowercase with underscores (snake_case): `get_connection()`, `is_relevant_incident()`, `create_html_email()`
- Private methods use underscore prefix: `_ensure_db_directory()`, `_generate_hash()`, `_load_logo()`
- Helper methods follow same pattern: `clean_location()`, `parse_time_string()`, `calculate_severity()`

**Variables:**
- Lowercase with underscores: `incident_hash`, `text_lower`, `central_tz`, `table_rows`, `email_configured`
- Boolean variables: `is_relevant`, `has_truck`, `has_spill`, `include_stalls`, `all_passed`
- Constants use UPPERCASE: `MAX_ALERTS_PER_HOUR`, `SCRAPE_INTERVAL`, `DATABASE_PATH`

**Types/Classes:**
- PascalCase for class names: `Database`, `Incident`, `Subscriber`, `HazmatSubscriber`, `EmailService`, `TranStarScraper`
- Database tables use lowercase with underscores: `incidents`, `subscribers`, `hazmat_subscribers`, `sent_alerts`, `admin_users`, `settings`

## Code Style

**Formatting:**
- No linting/formatting tool detected (no `.eslintrc`, `.prettierrc`, `pylint`, `black` config found)
- Consistent spacing: 4-space indentation throughout all Python files
- Blank lines between method definitions
- Long lines extend beyond 80 characters (no strict line length enforcement observed)

**Linting:**
- No detected linting configuration in place
- Code uses standard Python conventions implicitly

## Import Organization

**Order observed:**
1. Standard library imports: `import sqlite3`, `import logging`, `from datetime import datetime`
2. Third-party library imports: `import requests`, `from bs4 import BeautifulSoup`, `from flask import Flask`
3. Local module imports: `from config import Config`, `from models import Database`, `from scraper import TranStarScraper`

**Example from `app.py` (lines 1-17):**
```python
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import atexit
import logging
from datetime import datetime, timedelta
import re
from collections import deque
import pytz

from config import Config
from models import Database, Incident, Subscriber, HazmatSubscriber, AdminUser, SentAlert, Settings
from scraper import TranStarScraper
from email_service import EmailService
```

**Path Aliases:**
- Not used; all imports are relative or absolute

## Error Handling

**Patterns observed:**

**Try-Except blocks for database operations:**
```python
# From models.py line 217-230
try:
    cursor.execute('''
        INSERT INTO incidents (incident_hash, location, description, incident_time, severity)
        VALUES (?, ?, ?, ?, ?)
    ''', (self.incident_hash, self.location, self.description, self.incident_time, self.severity))

    incident_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return incident_id
except sqlite3.IntegrityError:
    # Incident already exists
    conn.close()
    return None
```

**Try-Except with logging in scheduled tasks:**
```python
# From app.py line 74-101
try:
    add_scrape_log("🔄 Starting scheduled scrape...")
    new_incidents = scraper.run_scrape_cycle()

    if new_incidents:
        # ... processing logic
except Exception as e:
    add_scrape_log(f"❌ Scheduled scrape error: {str(e)}", 'error')
```

**Return False/None pattern for failure cases:**
- Database operations return `False` on error: `return affected > 0` in `Subscriber.remove()`
- API calls return `None` on error: `return None` in `create_incident_from_api_data()`

## Logging

**Framework:** Python's standard `logging` module

**Setup pattern (from `app.py` line 19-21):**
```python
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

**Patterns:**
- Log levels used: `logger.info()`, `logger.warning()`, `logger.error()`
- Emoji-based messaging in logs for visual distinction:
  - `🔄` for starting operations
  - `✅` for successful operations
  - `❌` for errors
  - `📍` for location information
  - `📧` for email operations
  - `🕷️` for scraper operations
  - `🗄️` for database operations
  - `🌐` for Flask/web operations

**Example from `scraper.py` line 100-102:**
```python
if result:
    logger.info(f"✅ Relevant incident found: {text[:100]}...")

return result
```

**Custom log wrapper used in `app.py` (lines 27-41):**
```python
def add_scrape_log(message, level='info'):
    """Add a log entry with timestamp"""
    timestamp = datetime.now(central_tz).strftime('%Y-%m-%d %I:%M:%S %p CST')
    scrape_logs.append({
        'timestamp': timestamp,
        'message': message,
        'level': level
    })
    # Also log to regular logger
    if level == 'error':
        logger.error(message)
    elif level == 'warning':
        logger.warning(message)
    else:
        logger.info(message)
```

## Comments

**When to Comment:**
- Docstrings on functions explain purpose: `"""Add a log entry with timestamp"""`
- Inline comments explain non-obvious logic
- Database schema comments explain tables and fields
- Configuration comments explain environment variables

**JSDoc/TSDoc:**
- Not applicable (Python project, not TypeScript)
- Use docstrings with triple quotes for function documentation

**Example from `models.py` line 197-210:**
```python
def _generate_hash(self):
    """Generate unique hash for incident deduplication"""
    # Clean location and description for consistent hashing
    location_clean = self.location.lower().strip()
    description_clean = self.description.lower().strip()

    # Remove time-sensitive words
    time_words = ['reported', 'dispatched', 'responding', 'crews', 'updated']
    for word in time_words:
        description_clean = description_clean.replace(word, '')

    # Create hash from core incident data
    core_data = f"{location_clean}:{description_clean[:100]}"
    return hashlib.md5(core_data.encode()).hexdigest()
```

## Function Design

**Size:**
- Most functions are 10-50 lines
- Some utility functions smaller (5-10 lines)
- Email/template functions larger (100+ lines) for HTML generation
- `email_service.py`: longest file at 1124 lines with several large methods

**Parameters:**
- Simple positional parameters preferred: `def add(db, email):`
- Flask routes use `request.form` for POST data: `email = request.form['email']`
- Configuration parameters read from `Config` class or database

**Return Values:**
- Boolean for success/failure: `return True` or `return False`
- Object for successful creation: `return incident` or `return cursor.lastrowid`
- List for collections: `return [row[0] for row in cursor.fetchall()]`
- None for optional results: `return None`
- String for formatted output: `return f"data:image/png;base64,{encoded_string}"`

## Module Design

**Exports:**
- Classes defined at module level: `class Database:`, `class Incident:`, `class TranStarScraper:`
- Functions defined at module level: `def scheduled_scrape():`, `def add_scrape_log():`
- All classes/functions implicitly public (no `__all__` used)

**Barrel Files:**
- Not used; each module has focused responsibility
- `config.py`: Configuration management
- `models.py`: Data models and database operations
- `scraper.py`: Web scraping logic
- `email_service.py`: Email sending and formatting
- `app.py`: Flask application and routes

## Database Conventions

**SQL patterns in `models.py`:**
- Parameterized queries used throughout: `cursor.execute(..., (email,))`
- Database connections obtained fresh: `conn = db.get_connection()`
- Always close connections: `conn.close()`
- Explicit transaction control: `conn.commit()` on success

**Example from `models.py` line 266-278:**
```python
@staticmethod
def add(db, email):
    """Add new subscriber"""
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('INSERT INTO subscribers (email) VALUES (?)', (email,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False
```

## Flask Route Conventions

**All routes in `app.py`:**
- Decorator pattern: `@app.route('/path', methods=['GET', 'POST'])`
- Authentication check: `@login_required`
- Form data access: `request.form['field_name']`
- Flash messages for user feedback: `flash('message', 'success')` or `flash('message', 'error')`
- Redirect pattern: `redirect(url_for('function_name'))`

**Example from `app.py` line 210-228:**
```python
@app.route('/add_subscriber', methods=['POST'])
@login_required
def add_subscriber():
    """Add new subscriber"""
    email = request.form['email']

    if Subscriber.add(db, email):
        flash(f'Subscriber {email} added successfully!', 'success')
    else:
        flash(f'Subscriber {email} already exists', 'error')

    return redirect(url_for('subscribers'))
```

## API Response Conventions

**JSON responses in `app.py`:**
- Use `jsonify()` for JSON responses: `return jsonify({...})`
- Always include `timestamp`: `'timestamp': datetime.now().isoformat()`
- Dictionary keys use snake_case: `recent_incidents_count`, `active_subscribers`, `scraper_running`

**Example from `app.py` line 405-421:**
```python
@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for dashboard stats"""
    recent_incidents = Incident.get_recent(db, hours=24)
    total_subscribers = len(Subscriber.get_all(db))
    active_subscribers = len(Subscriber.get_all_active(db))
    alerts_today = SentAlert.get_recent_count(db, hours=24)

    return jsonify({
        'recent_incidents_count': len(recent_incidents),
        'total_subscribers': total_subscribers,
        'active_subscribers': active_subscribers,
        'alerts_today': alerts_today,
        'scraper_running': scheduler.running,
        'timestamp': datetime.now().isoformat()
    })
```

## String Formatting

**Preferred method:**
- f-strings used throughout: `f"✅ Found {len(new_incidents)} new incidents!"`
- For database strings with format(): `'... WHERE scraped_at > datetime('now', '-{} hours')'.format(hours)`

**Example from `scraper.py` line 251-256:**
```python
incident = Incident(
    location=location,
    description=description,
    incident_time=incident_time,
    severity=severity
)
```

---

*Convention analysis: 2026-02-03*
