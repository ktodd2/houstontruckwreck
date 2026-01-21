---
path: /Users/kurtistodd/houstontruckwreck-2/models.py
type: model
updated: 2026-01-20
status: active
---

# models.py

## Purpose

Defines the SQLite database schema and provides ORM-like data access classes for the Houston Traffic Monitor system. Handles database initialization, schema creation, and CRUD operations for incidents, subscribers (regular and hazmat), admin users, sent alerts, and application settings. Ensures data integrity through hash-based incident deduplication and provides timezone-aware timestamps.

## Exports

- `Database` - Connection manager that initializes schema and provides SQLite connections
- `Settings` - Static methods for key-value settings storage (get_setting, set_setting, get_include_stalls, set_include_stalls)
- `Incident` - Data class for traffic incidents with hash-based deduplication, save/query methods
- `Subscriber` - Static methods for managing regular alert subscribers (add, remove, get_all, toggle_active)
- `HazmatSubscriber` - Static methods for managing hazmat-only alert subscribers
- `AdminUser` - Static methods for admin authentication (authenticate, get_by_username)
- `SentAlert` - Static methods for tracking sent alerts and rate limiting (mark_sent, get_recent_count)

## Dependencies

- [[config]] - Database path configuration and default admin credentials
- sqlite3 - SQLite database driver
- werkzeug.security - Password hashing for admin authentication
- pytz - Central Time zone for incident timestamps
- hashlib - MD5 hashing for incident deduplication

## Used By

TBD

## Notes

Database auto-creates directory and initializes with default subscribers and admin user on first run. Incident deduplication uses MD5 hash of cleaned location + description to prevent duplicate alerts. The settings table stores key-value pairs for runtime configuration like include_stalls toggle.
