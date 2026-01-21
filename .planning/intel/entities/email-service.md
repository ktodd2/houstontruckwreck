---
path: /Users/kurtistodd/houstontruckwreck-2/email_service.py
type: service
updated: 2026-01-20
status: active
---

# email_service.py

## Purpose

Handles all email notification functionality for the Houston Traffic Monitor system. Generates HTML and plain-text emails for incident alerts, hazmat-specific alerts, test emails, and daily summaries with CSV attachments. Manages SMTP communication with Gmail, rate limiting to prevent spam, and includes embedded logo branding. Provides Google Maps links for incident locations.

## Exports

- `EmailService` - Main email service class with methods:
  - `send_alert(incidents)` - Send incident alerts to all active subscribers
  - `send_hazmat_alert(incidents)` - Send hazmat-only alerts to hazmat subscriber list
  - `send_test_email(test_email)` - Send configuration verification email
  - `send_daily_summary(target_email)` - Send midnight summary with CSV attachment
  - `create_html_email(incidents)` - Generate styled HTML email content
  - `create_text_email(incidents)` - Generate plain text fallback content
  - `generate_csv_data(incidents)` - Create CSV export of incidents
- `test_email_service()` - Standalone test function

## Dependencies

- [[models]] - Database, Subscriber, HazmatSubscriber, SentAlert, Incident models
- [[config]] - SMTP credentials, email settings, rate limit configuration
- smtplib - SMTP email sending
- ssl - Secure TLS connection
- pytz - Central Time zone for timestamps
- urllib.parse - URL encoding for Google Maps links

## Used By

TBD

## Notes

Embeds truckwreck.png logo as base64 in emails. Uses Gmail SMTP (smtp.gmail.com:587 with STARTTLS). Rate limited by MAX_ALERTS_PER_HOUR config. Severity-based color coding: red for high (4+), orange for medium (3), white for low. Daily summary includes categorized breakdown (wrecks, stalls, hazmat) with attached CSV.
