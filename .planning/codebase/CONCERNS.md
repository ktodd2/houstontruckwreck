# Codebase Concerns

**Analysis Date:** 2026-02-03

## Security Issues

**Debug Mode Enabled in Production:**
- Issue: Flask debug mode is enabled in `app.py:501` with `debug=True`, exposing interactive debugger and detailed error pages
- Files: `app.py`, `start_app.py:23`
- Risk: Debugger can be accessed by attackers to execute arbitrary code; detailed stack traces leak sensitive information about application structure and dependencies
- Fix approach: Conditionally disable debug mode in production using environment variable check. Use `os.environ.get('FLASK_ENV') != 'production'`

**Hardcoded Default Credentials:**
- Issue: Default admin credentials (`admin/admin123`) are stored in `config.py:31-32` and fall back to hardcoded values if env vars not set
- Files: `config.py`, `models.py:100-105` (initial creation)
- Risk: Anyone with access to code can access admin panel immediately after deployment
- Fix approach: Remove hardcoded fallback values; require explicit env var configuration or force credential change on first login via migration

**Insecure Temporary Database Location:**
- Issue: Production database uses `/tmp/database.db` in `config.py:11`, which can be world-readable and is cleared on system restart
- Files: `config.py`
- Risk: Database can be read by other processes; all data lost on server restart or crash
- Fix approach: Use persistent storage path (e.g., `/var/lib/houston-traffic-monitor/database.db` with proper permissions) or migrate to managed database service

**Hardcoded Email Credentials in Memory:**
- Issue: Email credentials stored as plain text in `EmailService.__init__()` (lines 25-26), held in memory for duration of application
- Files: `email_service.py:20-30`
- Risk: Memory dumps or process inspection could expose credentials; no credential rotation mechanism
- Fix approach: Use environment variables only (no fallbacks), implement credentials manager pattern or use OAuth2 for Gmail

**Exposed Admin Email Hardcoded:**
- Issue: Admin email `ktoddllc1@gmail.com` hardcoded in `app.py:108` and `app.py:366` for daily summary and test emails
- Files: `app.py`
- Risk: Identifies specific individual; email address now publicly visible in git history
- Fix approach: Move to configuration with environment variable; redact from commit history using `git-filter-repo`

**Default Subscribers in Database Initialization:**
- Issue: Three default subscriber emails hardcoded in `models.py:116-120`, including personal email addresses
- Files: `models.py`
- Risk: Personal email addresses now in git history and exposed in codebase; would spam these users indefinitely
- Fix approach: Remove hardcoded subscribers; load from environment or configuration file instead

## Tech Debt

**SQL Injection Vulnerability via String Formatting:**
- Issue: `Incident.get_recent()` and `SentAlert.get_recent_count()` use `.format()` for SQL placeholders instead of parameterized queries in `models.py:242` and `models.py:436`
- Files: `models.py:238-242`, `models.py:433-436`
- Impact: User-supplied `hours` parameter not validated; attacker can inject SQL code via API calls like `/api/recent_incidents?hours=1; DROP TABLE incidents; --`
- Fix approach: Use parameterized queries with `?` placeholder: `WHERE scraped_at > datetime('now', '-' || ? || ' hours')` and bind `hours` as parameter

**Missing Database Connection Resource Management:**
- Issue: Multiple database methods in `models.py` don't use context managers; if exceptions occur between `get_connection()` and `conn.close()`, connections leak
- Files: `models.py:23-26`, `models.py:150-173`, `models.py:232-246`, and 15+ other methods
- Impact: Long-running application exhausts SQLite file locks and connections; out-of-memory errors possible; blocking subsequent scrapes
- Fix approach: Implement context manager or `try/finally` blocks ensuring `conn.close()` always executes

**Multiple Scraper Implementations - Code Duplication:**
- Issue: Four separate scraper files exist: `scraper.py`, `improved_scraper.py`, `selenium_scraper.py`, and scrapers in other files with overlapping functionality
- Files: `scraper.py`, `improved_scraper.py:490`, `selenium_scraper.py:438`
- Impact: Bug fixes must be replicated across files; maintenance burden; only `scraper.py` is used; dead code cluttering repository
- Fix approach: Archive/delete unused scrapers (`improved_scraper.py`, `selenium_scraper.py`); consolidate into single, well-tested scraper module

**No Input Validation on Email Endpoints:**
- Issue: Email regex validation duplicated in three routes (`add_subscriber`, `add_hazmat_subscriber`, `test_email`) in `app.py:218-219`, `292`, `263`
- Files: `app.py:211-228`, `app.py:285-302`, `app.py:256-275`
- Impact: Changes to email validation must be made in three places; inconsistency risk; brittle regex `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$` rejects valid emails
- Fix approach: Extract validation to utility function in `models.py` or validation module; use `email-validator` library for RFC-compliant validation

**Scheduler Not Restarted on Crash:**
- Issue: `BackgroundScheduler` in `app.py:70` starts once at module load; if scraping function crashes, jobs may stop executing silently
- Files: `app.py:70-139`
- Impact: Incidents not scraped/alerted for unknown duration; no monitoring of scheduler health
- Fix approach: Add health check endpoint that verifies last execution timestamp and alerts if scraping stalled; implement automatic job restart or supervisor process

**Global Database Instance Pattern:**
- Issue: `Database()` created once in `app.py:53`, `EmailService`, and `TranStarScraper`, with no connection pooling
- Files: `app.py:53`, `email_service.py:22`, `scraper.py:33`, `models.py:9-14`
- Impact: Single bottleneck; under concurrent requests, SQLite locks cause performance degradation; thread-safety not guaranteed
- Fix approach: Use connection pooling (sqlalchemy) or manage single shared database handle with proper locking

**Rate Limiting Logic Flawed:**
- Issue: `send_alert()` in `email_service.py:305-308` counts total alerts per hour but doesn't prevent bursts; multiple manual scrapes in seconds bypass limit
- Files: `email_service.py:298-308`
- Impact: Rate limit (MAX_ALERTS_PER_HOUR=20) easily circumvented; can spam subscribers with 20 alerts in rapid succession
- Fix approach: Implement token bucket or sliding window; track alert timestamps not just count; add per-subscriber cooldown

## Known Issues & Fragile Areas

**Incident Deduplication Hash Inconsistent:**
- Issue: `Incident._generate_hash()` in `models.py:197-210` removes time-sensitive words but hash generation is fragile and brittle
- Files: `models.py:197-210`
- Why fragile: Whitespace/punctuation variations in incident descriptions can cause different hashes for same incident; removing hardcoded `time_words` list won't catch all variations
- Safe modification: Use normalized description (lowercase, remove punctuation, collapse whitespace) before hashing; test with real TranStar data
- Test coverage: No unit tests for hash collisions or consistency

**Email Template Rendering Unescaped:**
- Issue: Incident location and description inserted directly into HTML templates without escaping in `email_service.py:93-97`, `410`
- Files: `email_service.py:90-103`, `email_service.py:403-413`
- Why fragile: If TranStar response contains `<script>` or HTML special chars, email could be malformed or interpreted as code by some clients
- Safe modification: Use Jinja2 or `html.escape()` on all user-provided data before inserting into HTML
- Test coverage: No tests for malicious incident descriptions

**Stall Filtering Conditional Import:**
- Issue: `is_relevant_incident()` imports `Settings` inside the method at `scraper.py:93` rather than at module level
- Files: `scraper.py:41-102`, specifically `scraper.py:93`
- Why fragile: Circular import risk if Settings modified to import scraper; runtime import less efficient; unusual pattern confuses readers
- Safe modification: Move import to module top; verify no circular dependencies introduced

**Missing Incident Type Detection:**
- Issue: `Incident` model has `severity` field but no intelligent severity calculation; all incidents default to severity=1
- Files: `models.py:187-195`, `app.py:76-84` (severity guessing in email service)
- Impact: Severity logic split between scraper (should assign) and email service (tries to detect); no consistency
- Test coverage: Severity calculation never tested; email service guesses severity from keywords with no fallback

**Hazmat Alert Always Sent Together:**
- Issue: Both regular and hazmat alerts sent sequentially for same incident in `app.py:88-97`
- Files: `app.py:78-97`
- Impact: Subscribers could receive two emails for same hazmat incident; no deduplication between regular/hazmat alerts
- Safe modification: Check if incident already sent before sending hazmat alert; or consolidate into single alert channel

## Test Coverage Gaps

**No Unit Tests for Core Functions:**
- What's not tested: Email sending logic, incident deduplication, scraper filtering, database operations
- Files: `email_service.py` (1124 lines), `scraper.py` (490 lines), `models.py` (440 lines)
- Risk: Critical bugs in email sending (e.g., SMTP error handling) ship to production undetected
- Test files exist but test only integration/system behavior, not unit-testable functions

**Test Files Scattered and Ad-hoc:**
- Files: `test_system.py:183`, `test_improvements.py:230`, `test_incident_detection.py:136`
- Issue: Tests are script-based, not pytest-compatible; no test discovery; manual execution required
- Coverage: System tests exist but unit test coverage is 0% for core modules
- Priority: HIGH - Add pytest framework and parametrized unit tests for incident filtering logic

**No Error Scenario Testing:**
- Missing: SMTP failures, network timeouts, database locks, malformed API responses, TranStar service down
- Impact: Error handling paths untested; silent failures possible (e.g., email send fails, app continues with no alert)
- Priority: MEDIUM - Add integration tests for resilience

## Performance Concerns

**Inefficient Subscriber Queries:**
- Issue: `send_alert()` calls `Subscriber.get_all_active(db)` which fetches ALL subscribers into memory, then passes as single email recipient list
- Files: `email_service.py:310-311`, `email_service.py:330`
- Impact: With 1000+ subscribers, building large recipient list in memory; MIMEMultipart message size grows linearly
- Improvement: Batch emails (send to 50 subscribers per message) or use BCC list; current approach works until ~500 subscribers

**Scraper Creates New Session Per Endpoint:**
- Issue: `TranStarScraper.__init__()` creates `self.session` but `scrape_api_endpoints()` doesn't reuse it efficiently across four endpoints
- Files: `scraper.py:18-32`, `scraper.py:127-160`
- Impact: Minor; session reuse is correct, but redundant header setting per-request in some paths
- Improvement: Profile actual scrape times; likely not bottleneck

**In-Memory Log Buffer Not Bounded:**
- Issue: `scrape_logs` deque in `app.py:24` has `maxlen=100` but stores full timestamp+message strings for each scrape interval
- Files: `app.py:23-34`
- Impact: Negligible for current scale (100 * ~50 bytes = 5KB), but grows unbounded if called more frequently
- Improvement: Use rotating file logger instead; add `/api/scrape_logs` pagination

## Scaling Limits

**SQLite Not Production-Ready:**
- Current capacity: ~10K incidents, handles sequential reads fine
- Limit: Concurrent writes block; WAL mode helps but still single-file contention
- Scaling path: Migrate to PostgreSQL (easy: use SQLAlchemy); keep schema similar
- Blocking: None immediately, but plan before going production with load

**No Incident Retention Policy:**
- Issue: `Incident` table grows without bounds; no delete/archive logic
- Files: `models.py:33-44`
- Capacity: 1K incidents per day = 365K/year; SQLite can handle but queries slow as table grows
- Fix: Add migration to delete incidents older than 90 days; implement soft deletes with retention setting

**Single Scraper Instance Bottleneck:**
- Issue: One `TranStarScraper` instance runs all scrapes; if TranStar endpoint slow, entire alert cycle blocked
- Files: `scraper.py:16`, `app.py:54`
- Capacity: Current 60-second interval works; if shortened to 30s, TranStar API response time becomes critical
- Scaling: Add timeout to scraper requests (already has 15s timeout in line 136) and implement fallback/retry logic

## Missing Critical Features

**No Monitoring/Alerting on System Failure:**
- Missing: Alert to admin if scraper fails for N hours; email service down; database corrupted
- Impact: Could miss incidents for days without noticing
- Fix: Implement dead letter queue; send admin alert email if scraping stalled >2 hours

**No Incident Change Tracking:**
- Missing: History of incident status changes (e.g., "resolved", "in-progress", "cleared")
- Impact: Can't tell if incident is fresh or 8 hours old; subscribers confused
- Fix: Add `status` and `resolved_at` fields to Incident table; include in email

**No Subscriber Unsubscribe Mechanism:**
- Issue: No way for email recipients to unsubscribe without admin intervention
- Files: `email_service.py` (no unsubscribe link in emails)
- Risk: Violates CAN-SPAM/GDPR requirements; legal liability
- Fix: Add unsubscribe token generation; implement `/unsubscribe/{token}` endpoint

**No Incident Suppression/Blacklist:**
- Missing: Ability to mute recurring false positives (e.g., "I-45 construction" triggered daily)
- Impact: Email fatigue; users tune out real alerts
- Fix: Add blacklist table; regex or exact-match suppression; admin UI to manage

## Production Readiness Gaps

**No Graceful Shutdown:**
- Issue: Scheduler registered with `atexit` in `app.py:139` but no signal handlers (SIGTERM, SIGINT)
- Files: `app.py:138-139`
- Impact: Kubernetes/systemd sends SIGTERM; Flask debug server doesn't respect it; orphaned jobs remain running
- Fix: Implement `signal.signal()` handlers for graceful shutdown

**Logging Not Structured:**
- Issue: Logging mixed between `logger` and `print()` statements; no structured fields (request_id, incident_id)
- Files: Throughout codebase
- Impact: Hard to correlate logs across components; grep-based debugging only
- Fix: Use `python-json-logger` for structured logging; add context managers for request tracking

**No Environment Validation at Startup:**
- Issue: App starts successfully even if EMAIL_PASSWORD missing; only fails when sending alerts
- Files: `app.py:43-56` (no validation)
- Impact: Deploy broken system to production without knowing until first incident
- Fix: Add startup validation in `app.py` before starting scheduler; require critical env vars

**Health Check Incomplete:**
- Issue: `/health` endpoint checks database and scheduler but doesn't verify scraper responsiveness
- Files: `app.py:452-484`
- Impact: App reports "healthy" even if TranStar API unreachable; load balancer doesn't detect actual failure
- Fix: Add last_scrape_timestamp check; report unhealthy if no scrapes in last 3 * SCRAPE_INTERVAL

---

*Concerns audit: 2026-02-03*
