import sqlite3
import hashlib
import os
from datetime import datetime
import pytz
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DATABASE_PATH
        # Ensure the directory exists
        self._ensure_db_directory()
        self.init_db()
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"Created database directory: {db_dir}")
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create incidents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_hash TEXT UNIQUE NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                incident_time TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                severity INTEGER DEFAULT 1
            )
        ''')
        
        # Create subscribers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create sent_alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (incident_id) REFERENCES incidents (id)
            )
        ''')
        
        # Create admin_users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create default admin user if none exists
        cursor.execute('SELECT COUNT(*) FROM admin_users')
        if cursor.fetchone()[0] == 0:
            password_hash = generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD)
            cursor.execute(
                'INSERT INTO admin_users (username, password_hash) VALUES (?, ?)',
                (Config.DEFAULT_ADMIN_USERNAME, password_hash)
            )
        
        # Initialize default settings
        cursor.execute('SELECT COUNT(*) FROM settings WHERE setting_key = ?', ('include_stalls',))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                'INSERT INTO settings (setting_key, setting_value) VALUES (?, ?)',
                ('include_stalls', 'true')
            )
        
        # Add default subscribers if they don't exist
        default_subscribers = [
            'ktoddizzle@icloud.com',
            'branhar01@gmail.com'
        ]
        
        for email in default_subscribers:
            cursor.execute('SELECT COUNT(*) FROM subscribers WHERE email = ?', (email,))
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    'INSERT INTO subscribers (email, active) VALUES (?, 1)',
                    (email,)
                )
                print(f"Added default subscriber: {email}")
        
        conn.commit()
        conn.close()

class Settings:
    @staticmethod
    def get_setting(db, key, default=None):
        """Get a setting value"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT setting_value FROM settings WHERE setting_key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else default
    
    @staticmethod
    def set_setting(db, key, value):
        """Set a setting value"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_include_stalls(db):
        """Get the include_stalls setting as boolean"""
        value = Settings.get_setting(db, 'include_stalls', 'true')
        return value.lower() == 'true'
    
    @staticmethod
    def set_include_stalls(db, include):
        """Set the include_stalls setting"""
        value = 'true' if include else 'false'
        Settings.set_setting(db, 'include_stalls', value)

class Incident:
    def __init__(self, location, description, incident_time=None, severity=1):
        self.location = location
        self.description = description
        # Use Central Time for incident time
        central_tz = pytz.timezone('America/Chicago')
        self.incident_time = incident_time or datetime.now(central_tz).strftime('%I:%M %p')
        self.severity = severity
        self.incident_hash = self._generate_hash()
    
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
    
    def save(self, db):
        """Save incident to database if not already exists"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
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
    
    @staticmethod
    def get_recent(db, hours=24):
        """Get recent incidents"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM incidents 
            WHERE scraped_at > datetime('now', '-{} hours')
            ORDER BY scraped_at DESC
        '''.format(hours))
        
        incidents = cursor.fetchall()
        conn.close()
        return incidents
    
    @staticmethod
    def is_already_sent(db, incident_hash):
        """Check if alert was already sent for this incident"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT sa.id FROM sent_alerts sa
            JOIN incidents i ON sa.incident_id = i.id
            WHERE i.incident_hash = ?
        ''', (incident_hash,))
        
        result = cursor.fetchone()
        conn.close()
        return result is not None

class Subscriber:
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
    
    @staticmethod
    def remove(db, email):
        """Remove subscriber"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM subscribers WHERE email = ?', (email,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    @staticmethod
    def get_all_active(db):
        """Get all active subscribers"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT email FROM subscribers WHERE active = 1')
        subscribers = [row[0] for row in cursor.fetchall()]
        conn.close()
        return subscribers
    
    @staticmethod
    def get_all(db):
        """Get all subscribers with details"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM subscribers ORDER BY created_at DESC')
        subscribers = cursor.fetchall()
        conn.close()
        return subscribers
    
    @staticmethod
    def toggle_active(db, email):
        """Toggle subscriber active status"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE subscribers SET active = NOT active WHERE email = ?', (email,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

class AdminUser:
    @staticmethod
    def authenticate(db, username, password):
        """Authenticate admin user"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT password_hash FROM admin_users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result and check_password_hash(result[0], password):
            return True
        return False
    
    @staticmethod
    def get_by_username(db, username):
        """Get admin user by username"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM admin_users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        return user

class SentAlert:
    @staticmethod
    def mark_sent(db, incident_id):
        """Mark incident as having alert sent"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO sent_alerts (incident_id) VALUES (?)', (incident_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_recent_count(db, hours=1):
        """Get count of alerts sent in recent hours"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM sent_alerts 
            WHERE sent_at > datetime('now', '-{} hours')
        '''.format(hours))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
