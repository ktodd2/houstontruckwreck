from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import logging
from datetime import datetime, timedelta
import re

from config import Config
from models import Database, Incident, Subscriber, AdminUser, SentAlert, Settings
from scraper import TranStarScraper
from email_service import EmailService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.info("Running scheduled scrape...")
        new_incidents = scraper.run_scrape_cycle()
        
        if new_incidents:
            logger.info(f"Found {len(new_incidents)} new incidents, sending alerts...")
            success = email_service.send_alert(new_incidents)
            if success:
                logger.info("✅ Alerts sent successfully")
            else:
                logger.error("❌ Failed to send alerts")
        else:
            logger.info("No new incidents found")
            
    except Exception as e:
        logger.error(f"Error in scheduled scrape: {e}")

# Start the scheduler
scheduler.add_job(
    func=scheduled_scrape,
    trigger=IntervalTrigger(seconds=Config.SCRAPE_INTERVAL),
    id='scrape_job',
    name='Scrape TranStar for incidents',
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

@app.route('/manual_scrape', methods=['POST'])
@login_required
def manual_scrape():
    """Manually trigger a scrape"""
    try:
        new_incidents = scraper.run_scrape_cycle()
        
        if new_incidents:
            success = email_service.send_alert(new_incidents)
            if success:
                flash(f'Manual scrape completed! Found {len(new_incidents)} new incidents and sent alerts.', 'success')
            else:
                flash(f'Manual scrape found {len(new_incidents)} new incidents but failed to send alerts.', 'error')
        else:
            flash('Manual scrape completed! No new incidents found.', 'info')
            
    except Exception as e:
        flash(f'Manual scrape failed: {str(e)}', 'error')
    
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
