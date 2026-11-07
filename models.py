import sqlite3
import hashlib
import json
import os
from datetime import datetime, timedelta
import pytz
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from incident_identity import CENTRAL, normalize, location_key, occurrence_key, priority_flags, core_description

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
                severity INTEGER DEFAULT 1,
                transtar_url TEXT
            )
        ''')

        # Migrate existing databases that predate the transtar_url column
        cursor.execute("PRAGMA table_info(incidents)")
        if 'transtar_url' not in [row[1] for row in cursor.fetchall()]:
            cursor.execute('ALTER TABLE incidents ADD COLUMN transtar_url TEXT')

        # Additive migration: preserve existing IDs, hashes and sent-alert links.
        columns = {row[1] for row in cursor.execute('PRAGMA table_info(incidents)')}
        for name, definition in [('identity_key', 'TEXT'), ('alert_flags', 'INTEGER'),
                                 ('last_seen_at', 'TEXT')]:
            if name not in columns:
                cursor.execute(f'ALTER TABLE incidents ADD COLUMN {name} {definition}')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS incidents_identity_key ON incidents(identity_key)')

        # Create subscribers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                active BOOLEAN DEFAULT 1,
                receive_stalls BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migrate existing databases that predate the receive_stalls column
        cursor.execute("PRAGMA table_info(subscribers)")
        if 'receive_stalls' not in [row[1] for row in cursor.fetchall()]:
            cursor.execute('ALTER TABLE subscribers ADD COLUMN receive_stalls BOOLEAN DEFAULT 1')
        
        # Create hazmat_subscribers table (for hazmat/spill-only alerts)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hazmat_subscribers (
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
        
        # Addresses permitted to receive notifications, with each address's stall
        # preference: (email, receive_stalls). Ralaniz and Rayramon opted out of
        # stall alerts (they still receive wreck and hazmat alerts).
        ALLOWED_SUBSCRIBERS = [
            ('ktoddizzle@icloud.com', 1),
            ('Ralaniz911@yahoo.com', 0),
            ('Rayramon911@icloud.com', 0),
        ]
        ALLOWED_EMAILS = [email for email, _ in ALLOWED_SUBSCRIBERS]

        # Add default subscribers if they don't exist
        for email, receive_stalls in ALLOWED_SUBSCRIBERS:
            cursor.execute('SELECT COUNT(*) FROM subscribers WHERE email = ?', (email,))
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    'INSERT INTO subscribers (email, active, receive_stalls) VALUES (?, 1, ?)',
                    (email, receive_stalls)
                )
                print(f"Added default subscriber: {email}")

        # Add default hazmat subscribers if they don't exist (stall preference does
        # not apply to the hazmat list)
        for email in ALLOWED_EMAILS:
            cursor.execute('SELECT COUNT(*) FROM hazmat_subscribers WHERE email = ?', (email,))
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    'INSERT INTO hazmat_subscribers (email, active) VALUES (?, 1)',
                    (email,)
                )
                print(f"Added default hazmat subscriber: {email}")

        # Enforce the allowlist on every startup: remove any address that is not
        # permitted, so previously-seeded or manually-added addresses cannot linger
        # (or come back after a restart).
        placeholders = ','.join('?' for _ in ALLOWED_EMAILS)
        cursor.execute(f'DELETE FROM subscribers WHERE email NOT IN ({placeholders})', ALLOWED_EMAILS)
        cursor.execute(f'DELETE FROM hazmat_subscribers WHERE email NOT IN ({placeholders})', ALLOWED_EMAILS)

        # Enforce each address's stall preference on every startup so it stays
        # deterministic regardless of prior state.
        for email, receive_stalls in ALLOWED_SUBSCRIBERS:
            cursor.execute('UPDATE subscribers SET receive_stalls = ? WHERE email = ?', (receive_stalls, email))

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
    def __init__(self, location, description, incident_time=None, severity=1, transtar_url=None,
                 *, source_location=None, source_status=None, observed_at=None):
        self.location = location
        self.description = description
        # Use Central Time for incident time
        central_tz = pytz.timezone('America/Chicago')
        self.incident_time = incident_time or datetime.now(central_tz).strftime('%I:%M %p')
        self.severity = severity
        self.transtar_url = transtar_url
        self.observed_at = observed_at or datetime.now(CENTRAL)
        self.source_location = source_location or location
        # An explicitly empty status must stay unknown, not become scrape time.
        self.source_status = incident_time if source_status is None else source_status
        self.occurrence = occurrence_key(self.source_status, self.observed_at)
        self.alert_flags = priority_flags(description)
        self.is_update = False
        self.incident_hash = self._generate_hash()
        self.identity_key = self.incident_hash if self.occurrence else None
    
    def _generate_hash(self):
        """Use source location + occurrence, never mutable lanes, for timed rows."""
        parts = ['transtar-v2', location_key(self.source_location), self.occurrence]
        if self.occurrence is None:
            # No trustworthy time: do not merge different descriptions by location.
            parts += [self.observed_at.astimezone(CENTRAL).date().isoformat(),
                      normalize(self.description)]
        return hashlib.sha256(json.dumps(parts).encode()).hexdigest()

    def _legacy_match(self, conn):
        """Adopt one unambiguous old row without changing its ID or sent history."""
        if not self.occurrence:
            return None
        # Older display locations lost Before/After/Near. Do not guess which one.
        if location_key(self.source_location) != location_key(self.location):
            return None
        matches = []
        since = (self.observed_at.astimezone(pytz.UTC) - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
        for row in conn.execute('SELECT * FROM incidents WHERE identity_key IS NULL AND scraped_at >= ?', (since,)):
            if location_key(row['location']) != location_key(self.location):
                continue
            if core_description(row['description']) != core_description(self.description):
                continue
            try:
                observed = datetime.fromisoformat(row['scraped_at']).replace(tzinfo=pytz.UTC)
            except (ValueError, TypeError):
                continue
            if occurrence_key(row['incident_time'], observed) == self.occurrence:
                matches.append(row)
        return matches[0] if len(matches) == 1 else None
    
    def save(self, db):
        """Upsert an observation; return an alert ID only for new/priority changes.

        Serialize match/update/insert so simultaneous scrape jobs cannot both
        queue the same new event or escalation. This is not an SMTP outbox.
        """
        conn = db.get_connection()
        try:
            with conn:
                conn.execute('BEGIN IMMEDIATE')
                row = conn.execute('SELECT * FROM incidents WHERE identity_key = ? OR incident_hash = ?',
                                   (self.identity_key, self.incident_hash)).fetchone()
                row = row if row is not None else self._legacy_match(conn)
                seen_at = self.observed_at.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
                if row is not None:
                    self.record_id = row['id']
                    previous_flags = row['alert_flags']
                    if previous_flags is None:
                        previous_flags = priority_flags(row['description'])
                    self.is_update = bool(self.alert_flags & ~previous_flags)
                    conn.execute('''
                        UPDATE incidents SET identity_key = ?, description = ?, incident_time = ?,
                            severity = ?, transtar_url = COALESCE(?, transtar_url),
                            alert_flags = ?, last_seen_at = ? WHERE id = ?
                    ''', (self.identity_key, self.description, self.incident_time, self.severity,
                          self.transtar_url, previous_flags | self.alert_flags, seen_at, row['id']))
                    # Retain legacy hashes so existing sent-alert lookups keep working.
                    self.incident_hash = row['incident_hash']
                    return row['id'] if self.is_update else None
                cursor = conn.execute('''
                    INSERT INTO incidents (incident_hash, location, description, incident_time, severity,
                        transtar_url, identity_key, alert_flags, last_seen_at, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (self.incident_hash, self.location, self.description, self.incident_time, self.severity,
                      self.transtar_url, self.identity_key, self.alert_flags, seen_at, seen_at))
                self.record_id = cursor.lastrowid
                return self.record_id
        finally:
            conn.close()
    
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
    def get_all_active_with_stalls(db):
        """Get all active subscribers with their stall preference.

        Returns a list of (email, receive_stalls_bool) tuples.
        """
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT email, receive_stalls FROM subscribers WHERE active = 1')
        subscribers = [(row[0], bool(row[1])) for row in cursor.fetchall()]
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


class HazmatSubscriber:
    @staticmethod
    def add(db, email):
        """Add new hazmat subscriber"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO hazmat_subscribers (email) VALUES (?)', (email,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    @staticmethod
    def remove(db, email):
        """Remove hazmat subscriber"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM hazmat_subscribers WHERE email = ?', (email,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    @staticmethod
    def get_all_active(db):
        """Get all active hazmat subscribers"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT email FROM hazmat_subscribers WHERE active = 1')
        subscribers = [row[0] for row in cursor.fetchall()]
        conn.close()
        return subscribers
    
    @staticmethod
    def get_all(db):
        """Get all hazmat subscribers with details"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM hazmat_subscribers ORDER BY created_at DESC')
        subscribers = cursor.fetchall()
        conn.close()
        return subscribers
    
    @staticmethod
    def toggle_active(db, email):
        """Toggle hazmat subscriber active status"""
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute('UPDATE hazmat_subscribers SET active = NOT active WHERE email = ?', (email,))
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

