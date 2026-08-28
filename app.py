from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import atexit
import hmac
import json
import logging
import os
from datetime import datetime, timedelta
import re
import time
from collections import deque
from urllib.parse import quote_plus
import pytz
import requests

from config import Config
from models import Database, Incident, Subscriber, HazmatSubscriber, AdminUser, SentAlert, Settings
from scraper import TranStarScraper
from email_service import EmailService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory circular buffer for scraping logs (keeps last 100 log entries)
scrape_logs = deque(maxlen=100)
central_tz = pytz.timezone('America/Chicago')

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

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the admin panel.'

# Initialize components
db = Database()
scraper = TranStarScraper()
email_service = EmailService()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(username):
    user_data = AdminUser.get_by_username(db, username)
    if user_data:
        return User(username)
    return None

# Background scheduler for scraping
scheduler = BackgroundScheduler()

def scheduled_scrape():
    """Background task to scrape for incidents"""
    try:
        add_scrape_log("🔄 Starting scheduled scrape...")
        new_incidents = scraper.run_scrape_cycle()
        
        if new_incidents:
            add_scrape_log(f"✅ Found {len(new_incidents)} new incidents!", 'info')
            
            # Log incident details
            for incident, incident_id in new_incidents:
                add_scrape_log(f"📍 {incident.location}: {incident.description}")
            
            add_scrape_log("📧 Sending alerts to subscribers...")
            
            # Send regular alerts to all subscribers
            success = email_service.send_alert(new_incidents)
            if success:
                add_scrape_log("✅ Regular alerts sent successfully", 'info')
            else:
                add_scrape_log("❌ Failed to send regular alerts", 'error')

            # Send hazmat-specific alerts to hazmat subscribers
            hazmat_success = email_service.send_hazmat_alert(new_incidents)
            if hazmat_success:
                add_scrape_log("✅ Hazmat alerts sent successfully", 'info')
        else:
            add_scrape_log("ℹ️  No new incidents found")
            
    except Exception as e:
        add_scrape_log(f"❌ Error in scheduled scrape: {e}", 'error')

def send_daily_summary():
    """Background task to send daily summary email at midnight"""
    try:
        logger.info("🕛 Running daily summary task...")
        success = email_service.send_daily_summary(target_email="ktoddizzle@icloud.com")
        
        if success:
            logger.info("✅ Daily summary sent successfully")
        else:
            logger.error("❌ Failed to send daily summary")
            
    except Exception as e:
        logger.error(f"Error in daily summary task: {e}")

# Start the scheduler
scheduler.add_job(
    func=scheduled_scrape,
    trigger=IntervalTrigger(seconds=Config.SCRAPE_INTERVAL),
    id='scrape_job',
    name='Scrape TranStar for incidents',
    replace_existing=True
)

# Add daily summary job - runs at midnight Central Time
scheduler.add_job(
    func=send_daily_summary,
    trigger=CronTrigger(hour=0, minute=0, timezone='America/Chicago'),
    id='daily_summary_job',
    name='Send daily summary email at midnight',
    replace_existing=True
)

scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    """Redirect to login or dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if AdminUser.authenticate(db, username, password):
            user = User(username)
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout admin user"""
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    # Get recent incidents
    recent_incidents = Incident.get_recent(db, hours=24)
    
    # Get system stats
    total_subscribers = len(Subscriber.get_all(db))
    active_subscribers = len(Subscriber.get_all_active(db))
    alerts_today = SentAlert.get_recent_count(db, hours=24)
    alerts_this_hour = SentAlert.get_recent_count(db, hours=1)
    
    # Get scheduler status
    scraper_running = scheduler.running
    next_run = None
    if scraper_running:
        jobs = scheduler.get_jobs()
        if jobs:
            next_run = jobs[0].next_run_time
    
    return render_template('dashboard.html',
                         recent_incidents=recent_incidents,
                         total_subscribers=total_subscribers,
                         active_subscribers=active_subscribers,
                         alerts_today=alerts_today,
                         alerts_this_hour=alerts_this_hour,
                         scraper_running=scraper_running,
                         next_run=next_run,
                         scrape_interval=Config.SCRAPE_INTERVAL)

@app.route('/subscribers')
@login_required
def subscribers():
    """Subscriber management page"""
    all_subscribers = Subscriber.get_all(db)
    return render_template('subscribers.html', subscribers=all_subscribers)

@app.route('/add_subscriber', methods=['POST'])
@login_required
def add_subscriber():
    """Add new subscriber"""
    email = request.form['email'].strip().lower()
    
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        flash('Invalid email format', 'error')
        return redirect(url_for('subscribers'))
    
    if Subscriber.add(db, email):
        flash(f'Subscriber {email} added successfully!', 'success')
    else:
        flash(f'Subscriber {email} already exists', 'error')
    
    return redirect(url_for('subscribers'))

@app.route('/remove_subscriber', methods=['POST'])
@login_required
def remove_subscriber():
    """Remove subscriber"""
    email = request.form['email']
    
    if Subscriber.remove(db, email):
        flash(f'Subscriber {email} removed successfully!', 'success')
    else:
        flash(f'Subscriber {email} not found', 'error')
    
    return redirect(url_for('subscribers'))

@app.route('/toggle_subscriber', methods=['POST'])
@login_required
def toggle_subscriber():
    """Toggle subscriber active status"""
    email = request.form['email']
    
    if Subscriber.toggle_active(db, email):
        flash(f'Subscriber {email} status updated!', 'success')
    else:
        flash(f'Subscriber {email} not found', 'error')
    
    return redirect(url_for('subscribers'))

@app.route('/test_email', methods=['POST'])
@login_required
def test_email():
    """Send test email"""
    test_email = request.form['test_email'].strip().lower()
    
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, test_email):
        flash('Invalid email format', 'error')
        return redirect(url_for('subscribers'))
    
    success = email_service.send_test_email(test_email)
    
    if success:
        flash(f'Test email sent successfully to {test_email}!', 'success')
    else:
        flash(f'Failed to send test email to {test_email}', 'error')
    
    return redirect(url_for('subscribers'))


@app.route('/hazmat_subscribers')
@login_required
def hazmat_subscribers():
    """Hazmat subscriber management page"""
    all_hazmat_subscribers = HazmatSubscriber.get_all(db)
    return render_template('hazmat_subscribers.html', hazmat_subscribers=all_hazmat_subscribers)

@app.route('/add_hazmat_subscriber', methods=['POST'])
@login_required
def add_hazmat_subscriber():
    """Add new hazmat subscriber"""
    email = request.form['email'].strip().lower()
    
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        flash('Invalid email format', 'error')
        return redirect(url_for('hazmat_subscribers'))
    
    if HazmatSubscriber.add(db, email):
        flash(f'Hazmat subscriber {email} added successfully!', 'success')
    else:
        flash(f'Hazmat subscriber {email} already exists', 'error')
    
    return redirect(url_for('hazmat_subscribers'))

@app.route('/remove_hazmat_subscriber', methods=['POST'])
@login_required
def remove_hazmat_subscriber():
    """Remove hazmat subscriber"""
    email = request.form['email']
    
    if HazmatSubscriber.remove(db, email):
        flash(f'Hazmat subscriber {email} removed successfully!', 'success')
    else:
        flash(f'Hazmat subscriber {email} not found', 'error')
    
    return redirect(url_for('hazmat_subscribers'))

@app.route('/toggle_hazmat_subscriber', methods=['POST'])
@login_required
def toggle_hazmat_subscriber():
    """Toggle hazmat subscriber active status"""
    email = request.form['email']
    
    if HazmatSubscriber.toggle_active(db, email):
        flash(f'Hazmat subscriber {email} status updated!', 'success')
    else:
        flash(f'Hazmat subscriber {email} not found', 'error')
    
    return redirect(url_for('hazmat_subscribers'))


@app.route('/manual_scrape', methods=['POST'])
@login_required
def manual_scrape():
    """Manually trigger a scrape"""
    try:
        add_scrape_log("🔄 Manual scrape initiated by user")
        new_incidents = scraper.run_scrape_cycle()
        
        if new_incidents:
            add_scrape_log(f"✅ Manual scrape found {len(new_incidents)} new incidents!")
            for incident, incident_id in new_incidents:
                add_scrape_log(f"📍 {incident.location}: {incident.description}")
            
            success = email_service.send_alert(new_incidents)
            if success:
                add_scrape_log("✅ Alerts sent successfully")
                flash(f'Manual scrape completed! Found {len(new_incidents)} new incidents and sent alerts.', 'success')
            else:
                add_scrape_log("❌ Failed to send alerts", 'error')
                flash(f'Manual scrape found {len(new_incidents)} new incidents but failed to send alerts.', 'error')
        else:
            add_scrape_log("ℹ️  Manual scrape: No new incidents found")
            flash('Manual scrape completed! No new incidents found.', 'info')
            
    except Exception as e:
        add_scrape_log(f"❌ Manual scrape failed: {str(e)}", 'error')
        flash(f'Manual scrape failed: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/test_daily_summary', methods=['POST'])
@login_required
def test_daily_summary():
    """Manually trigger daily summary email (for testing)"""
    try:
        success = email_service.send_daily_summary(target_email="ktoddizzle@icloud.com")
        
        if success:
            flash('Daily summary email sent successfully to ktoddizzle@icloud.com!', 'success')
        else:
            flash('Failed to send daily summary email.', 'error')
            
    except Exception as e:
        flash(f'Daily summary failed: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/settings')
@login_required
def settings():
    """Settings page"""
    include_stalls = Settings.get_include_stalls(db)
    return render_template('settings.html',
                         scrape_interval=Config.SCRAPE_INTERVAL,
                         max_alerts_per_hour=Config.MAX_ALERTS_PER_HOUR,
                         email_configured=bool(Config.EMAIL_USERNAME and Config.EMAIL_PASSWORD),
                         include_stalls=include_stalls)

@app.route('/toggle_stalls', methods=['POST'])
@login_required
def toggle_stalls():
    """Toggle heavy truck stall alerts"""
    try:
        current_setting = Settings.get_include_stalls(db)
        new_setting = not current_setting
        Settings.set_include_stalls(db, new_setting)
        
        status = "enabled" if new_setting else "disabled"
        flash(f'Heavy truck stall alerts {status} successfully!', 'success')
    except Exception as e:
        flash(f'Failed to update stall setting: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

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

@app.route('/api/recent_incidents')
@login_required
def api_recent_incidents():
    """API endpoint for recent incidents"""
    hours = request.args.get('hours', 24, type=int)
    incidents = Incident.get_recent(db, hours=hours)
    
    incidents_data = []
    for incident in incidents:
        incidents_data.append({
            'id': incident['id'],
            'location': incident['location'],
            'description': incident['description'],
            'incident_time': incident['incident_time'],
            'scraped_at': incident['scraped_at'],
            'severity': incident['severity']
        })
    
    return jsonify(incidents_data)

@app.route('/api/scrape_logs')
@login_required
def api_scrape_logs():
    """API endpoint for scraping logs"""
    # Return logs in reverse order (newest first)
    logs_list = list(scrape_logs)
    logs_list.reverse()
    return jsonify(logs_list)

# ---------------------------------------------------------------------------
# Live wall dashboard
# ---------------------------------------------------------------------------

# Keyword sets used to bucket an incident into a lane on the live wall.
HAZMAT_KEYWORDS = ('hazmat', 'hazardous material', 'chemical', 'spill',
                   'leak', 'leaking', 'fuel spill', 'oil spill')
WRECK_KEYWORDS = ('accident', 'crash', 'collision', 'rollover', 'roll over',
                  'jackknife', 'jack-knife', 'overturned', 'wreck')
STALL_KEYWORDS = ('stall', 'stalled', 'disabled', 'broke down', 'breakdown')


def classify_incident(text):
    """Bucket an incident into hazmat / wreck / stall / other.

    Hazmat wins over everything, then wrecks, then stalls — an incident that
    mentions both a spill and a crash belongs at the top of the board.
    """
    t = (text or '').lower()
    if any(k in t for k in HAZMAT_KEYWORDS):
        return 'hazmat'
    if any(k in t for k in WRECK_KEYWORDS):
        return 'wreck'
    if any(k in t for k in STALL_KEYWORDS):
        return 'stall'
    return 'other'


def _incident_payload(row):
    """Turn an incidents row into the shape the live wall renders."""
    location = row['location'] or ''
    description = row['description'] or ''
    scraped_at = row['scraped_at']

    # scraped_at is stored by SQLite as UTC ("YYYY-MM-DD HH:MM:SS").
    scraped_iso = None
    age_minutes = None
    try:
        dt = datetime.strptime(str(scraped_at)[:19], '%Y-%m-%d %H:%M:%S')
        dt = pytz.utc.localize(dt)
        scraped_iso = dt.isoformat()
        age_minutes = int((datetime.now(pytz.utc) - dt).total_seconds() // 60)
    except (ValueError, TypeError):
        pass

    return {
        'id': row['id'],
        'location': location,
        'description': description,
        'incident_time': row['incident_time'],
        'scraped_at': scraped_at,
        'scraped_iso': scraped_iso,
        'age_minutes': age_minutes,
        'severity': row['severity'],
        'category': classify_incident(f"{location} {description}"),
        'map_url': ('https://www.google.com/maps/search/?api=1&query='
                    + _maps_query(location)) if location else None,
    }


def _maps_query(location):
    """URL-encode a TranStar location for a Google Maps search link.

    Google Maps reads 'Main St and Elm St' as an intersection but chokes on
    the 'Main St @ Elm St' form TranStar uses, so swap the separators the way
    the email alerts and admin dashboard already do, and anchor the search to
    Houston so a generic street pair doesn't land in another city.
    """
    formatted = (location.replace(' @ ', ' and ').replace('@', ' and ')
                 .replace(' at ', ' and ').replace(' AT ', ' and '))
    return quote_plus(formatted + ' Houston TX')


# A briefing card stops being shown once it is this old, so a task that
# stops running leaves an empty panel rather than yesterday's news looking
# like today's.
BRIEFING_MAX_AGE_HOURS = 48


def _load_briefings():
    """Read the briefing cards pushed in by the scheduled tasks."""
    raw = Settings.get_setting(db, 'live_briefings', None)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, dict):
        return []

    cutoff = datetime.now(central_tz) - timedelta(hours=BRIEFING_MAX_AGE_HOURS)
    cards = []
    for key, card in data.items():
        if not isinstance(card, dict):
            continue
        try:
            updated = datetime.fromisoformat(card.get('updated_at'))
            if updated < cutoff:
                continue
        except (ValueError, TypeError):
            # Undateable card: keep it rather than silently dropping content.
            pass
        card = dict(card)
        card['key'] = key
        cards.append(card)
    cards.sort(key=lambda c: c.get('updated_at') or '', reverse=True)
    return cards


# ---------- driveshaftcable.com store feed ----------
# The live wall shows unfilled orders and sales KPIs pulled from the store's
# Supabase edge function. Cached so 20-second polling from however many open
# wall tabs costs at most one upstream call per STORE_STATS_CACHE_SECONDS,
# and the last good payload is served (marked stale) if the upstream hiccups.
_store_cache = {'at': 0.0, 'data': None}


def _fetch_store_stats():
    if not Config.STORE_STATS_TOKEN:
        return {'ok': False, 'error': 'store feed not configured — set STORE_STATS_TOKEN'}

    now = time.time()
    if _store_cache['data'] is not None and now - _store_cache['at'] < Config.STORE_STATS_CACHE_SECONDS:
        return _store_cache['data']

    try:
        resp = requests.get(
            Config.STORE_STATS_URL,
            headers={'Authorization': 'Bearer ' + Config.STORE_STATS_TOKEN},
            timeout=8,
        )
        if resp.ok:
            data = resp.json()
        else:
            data = {'ok': False, 'error': 'store feed returned HTTP %s' % resp.status_code}
    except (requests.RequestException, ValueError) as exc:
        data = {'ok': False, 'error': str(exc)}

    if data.get('ok'):
        _store_cache['data'] = data
        _store_cache['at'] = now
        return data

    # Upstream failed: serve the previous good payload, flagged, so the wall
    # degrades to "slightly old numbers" instead of an empty panel.
    if _store_cache['data'] is not None:
        stale = dict(_store_cache['data'])
        stale['stale'] = True
        stale['stale_error'] = data.get('error')
        return stale
    return data


@app.route('/live')
@login_required
def live():
    """Full-screen always-on wall dashboard."""
    return render_template('live.html', scrape_interval=Config.SCRAPE_INTERVAL)


@app.route('/api/live')
@login_required
def api_live():
    """Everything the live wall needs, in one call."""
    hours = request.args.get('hours', 24, type=int)
    rows = Incident.get_recent(db, hours=hours)
    incidents = [_incident_payload(r) for r in rows]

    counts = {'hazmat': 0, 'wreck': 0, 'stall': 0, 'other': 0}
    for item in incidents:
        counts[item['category']] = counts.get(item['category'], 0) + 1

    # Scheduler status
    next_run_iso = None
    next_run_label = None
    jobs = scheduler.get_jobs() if scheduler.running else []
    for job in jobs:
        if job.id == 'scrape_job' and job.next_run_time:
            next_run_iso = job.next_run_time.isoformat()
            next_run_label = job.next_run_time.astimezone(central_tz).strftime('%I:%M:%S %p')
            break

    logs = list(scrape_logs)
    logs.reverse()

    now = datetime.now(central_tz)
    return jsonify({
        'generated_at': now.isoformat(),
        'generated_label': now.strftime('%I:%M:%S %p CST'),
        'window_hours': hours,
        'counts': counts,
        'total_incidents': len(incidents),
        'incidents': incidents,
        'stats': {
            'total_subscribers': len(Subscriber.get_all(db)),
            'active_subscribers': len(Subscriber.get_all_active(db)),
            'hazmat_subscribers': len(HazmatSubscriber.get_all_active(db)),
            'alerts_today': SentAlert.get_recent_count(db, hours=24),
            'alerts_this_hour': SentAlert.get_recent_count(db, hours=1),
        },
        'scraper': {
            'running': scheduler.running,
            'interval_seconds': Config.SCRAPE_INTERVAL,
            'next_run_iso': next_run_iso,
            'next_run_label': next_run_label,
            'include_stalls': Settings.get_include_stalls(db),
        },
        'logs': logs[:40],
        'briefings': _load_briefings(),
        'store': _fetch_store_stats(),
    })


@app.route('/api/briefing_token')
@login_required
def api_briefing_token():
    """Show the logged-in admin the token automations must present.

    Kept behind the admin login so the token is never readable anonymously.
    """
    token = Config.BRIEFING_TOKEN
    return jsonify({
        'configured': bool(token),
        'token': token,
        'source': ('BRIEFING_TOKEN env var' if os.environ.get('BRIEFING_TOKEN')
                   else ('derived from SECRET_KEY' if token else
                         'unavailable — set BRIEFING_TOKEN or a real SECRET_KEY')),
        'post_to': url_for('api_briefing', _external=True),
    })


@app.route('/api/briefing', methods=['POST'])
def api_briefing():
    """Accept a briefing card from an external scheduled task.

    Auth is a bearer token (BRIEFING_TOKEN) rather than a login session, so a
    headless automation can post here. Returns 503 until the token is set, so
    an unconfigured deploy can never be written to anonymously.
    """
    token = Config.BRIEFING_TOKEN
    if not token:
        return jsonify({'error': 'briefing endpoint not configured'}), 503

    supplied = request.headers.get('Authorization', '')
    if supplied.startswith('Bearer '):
        supplied = supplied[7:]
    if not hmac.compare_digest(supplied, token):
        return jsonify({'error': 'unauthorized'}), 401

    payload = request.get_json(silent=True) or {}
    key = str(payload.get('key') or '').strip()
    if not key:
        return jsonify({'error': 'key is required'}), 400

    items = payload.get('items') or []
    clean_items = []
    for item in items[:8]:
        if not isinstance(item, dict):
            continue
        clean_items.append({
            'headline': str(item.get('headline') or '')[:300],
            'detail': str(item.get('detail') or '')[:600],
            'url': str(item.get('url') or '')[:600],
        })

    card = {
        'title': str(payload.get('title') or key)[:120],
        'subtitle': str(payload.get('subtitle') or '')[:300],
        'url': str(payload.get('url') or '')[:600],
        'status': str(payload.get('status') or 'ok')[:40],
        'items': clean_items,
        'updated_at': datetime.now(central_tz).isoformat(),
        'updated_label': datetime.now(central_tz).strftime('%b %d, %I:%M %p CST'),
    }

    raw = Settings.get_setting(db, 'live_briefings', None)
    try:
        store = json.loads(raw) if raw else {}
        if not isinstance(store, dict):
            store = {}
    except (ValueError, TypeError):
        store = {}

    store[key] = card
    Settings.set_setting(db, 'live_briefings', json.dumps(store))
    add_scrape_log(f"📰 Briefing '{key}' updated from scheduled task")

    return jsonify({'ok': True, 'key': key, 'updated_at': card['updated_at']})


@app.route('/health')
def health():
    """Health check endpoint for load balancers and monitoring"""
    checks = {
        "database": False,
        "scheduler": False,
        "email_configured": False
    }

    # Check database connectivity
    try:
        conn = db.get_connection()
        conn.execute("SELECT 1")
        conn.close()
        checks["database"] = True
    except Exception:
        pass

    # Check scheduler is running
    checks["scheduler"] = scheduler.running

    # Check email is configured
    checks["email_configured"] = bool(Config.EMAIL_USERNAME and Config.EMAIL_PASSWORD)

    # Determine overall health
    # App is healthy if database and scheduler work (email config is a warning, not failure)
    is_healthy = checks["database"] and checks["scheduler"]

    return jsonify({
        "status": "healthy" if is_healthy else "unhealthy",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }), 200 if is_healthy else 503

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print("🚛 Houston Traffic Monitor Starting...")
    print(f"📊 Dashboard will be available at: http://localhost:5000")
    print(f"👤 Default admin login: {Config.DEFAULT_ADMIN_USERNAME} / {Config.DEFAULT_ADMIN_PASSWORD}")
    print(f"⏱️  Scraping interval: {Config.SCRAPE_INTERVAL} seconds")
    print(f"📧 Email configured: {bool(Config.EMAIL_USERNAME and Config.EMAIL_PASSWORD)}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
