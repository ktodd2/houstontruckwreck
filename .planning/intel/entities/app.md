---
path: /Users/kurtistodd/houstontruckwreck-2/app.py
type: api
updated: 2026-01-20
status: active
---

# app.py

## Purpose

Main Flask web application that serves as the admin dashboard and API for the Houston Traffic Monitor system. Orchestrates background scraping jobs via APScheduler, handles user authentication with Flask-Login, manages subscriber CRUD operations, and exposes REST endpoints for dashboard statistics. This is the central entry point that ties together scraping, email alerting, and database operations.

## Exports

- `app` - Flask application instance configured with routes, login manager, and scheduler
- `add_scrape_log(message, level)` - Utility function to add timestamped log entries to circular buffer
- `scheduled_scrape()` - Background task that runs scrape cycles and sends alerts
- `send_daily_summary()` - Background task for midnight daily summary emails
- `User` - Flask-Login compatible user class wrapping admin usernames

## Dependencies

- [[config]] - Application configuration (secret key, scrape interval, email settings)
- [[models]] - Database class and ORM models (Incident, Subscriber, HazmatSubscriber, AdminUser, SentAlert, Settings)
- [[scraper]] - TranStarScraper class for fetching traffic incidents
- [[email-service]] - EmailService class for sending alert and summary emails
- flask - Web framework for routing and request handling
- flask-login - Session-based user authentication
- apscheduler - Background job scheduling for periodic scraping
- pytz - Timezone handling for Central Time display

## Used By

TBD

## Notes

Uses a circular buffer (deque maxlen=100) to store scraping logs in memory for dashboard display. The scheduler runs two jobs: scraping at configurable intervals and a daily summary at midnight CST.
