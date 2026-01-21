---
path: /Users/kurtistodd/houstontruckwreck-2/improved_scraper.py
type: service
updated: 2026-01-20
status: active
---

# improved_scraper.py

## Purpose

Alternative implementation of the TranStar traffic scraper with identical functionality to scraper.py. Provides the ImprovedTranStarScraper class as a drop-in replacement for TranStarScraper. Uses the same API-first strategy with HTML fallback, same keyword filtering for truck/hazmat incidents, and same severity calculation algorithm. Exists as a refactored version that can be swapped in if needed.

## Exports

- `ImprovedTranStarScraper` - Scraper class with methods:
  - `run_scrape_cycle()` - Complete scrape/filter/save workflow
  - `scrape_incidents()` - Fetch and parse incidents from TranStar
  - `scrape_api_endpoints()` - Try JSON API endpoints first
  - `scrape_html_fallback()` - Parse HTML tables if APIs fail
  - `is_relevant_incident(incident_data)` - Filter by truck/hazmat keywords
  - `save_new_incidents(incidents)` - Persist new incidents to database
  - `calculate_severity(description)` - Score incident urgency 1-5
- `test_improved_scraper()` - Standalone test function

## Dependencies

- [[models]] - Incident model for persistence, Database for storage, Settings for stall toggle
- [[config]] - Base URL and configuration settings
- requests - HTTP client for API and HTML fetching
- beautifulsoup4 - HTML parsing for fallback scraping
- pytz - Central Time zone handling

## Used By

TBD

## Notes

Functionally equivalent to scraper.py with the same API endpoints, keyword lists, and filtering logic. The class is named ImprovedTranStarScraper vs TranStarScraper. May represent an iterative development approach where both versions are kept for comparison or rollback purposes.
