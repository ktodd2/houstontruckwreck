---
path: /Users/kurtistodd/houstontruckwreck-2/config.py
type: config
updated: 2026-01-20
status: active
---

# config.py

## Purpose

Centralized configuration management for the Houston Traffic Monitor application. Loads environment variables from .env file and provides sensible defaults for development. Handles environment-specific settings like database path (local vs Render deployment) and exposes all configurable parameters as class attributes.

## Exports

- `Config` - Configuration class with attributes:
  - `SECRET_KEY` - Flask session secret
  - `DATABASE_PATH` - SQLite database location (/tmp for Render, local otherwise)
  - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_FROM` - SMTP settings
  - `SCRAPE_INTERVAL` - Seconds between scrape cycles (default 60)
  - `TRANSTAR_URL` - Houston TranStar road closures URL
  - `MAX_ALERTS_PER_HOUR` - Rate limiting threshold (default 20)
  - `DEFAULT_ADMIN_USERNAME`, `DEFAULT_ADMIN_PASSWORD` - Initial admin credentials
  - `INCLUDE_STALLS` - Whether to include heavy truck stalls in alerts

## Dependencies

- python-dotenv - Environment variable loading from .env file
- os - Environment variable access and path handling

## Used By

TBD

## Notes

Detects Render deployment via RENDER environment variable to use /tmp for database (ephemeral storage). All sensitive values (email credentials, admin password) should be set via environment variables in production. SCRAPE_INTERVAL and MAX_ALERTS_PER_HOUR can be tuned for different monitoring intensities.
