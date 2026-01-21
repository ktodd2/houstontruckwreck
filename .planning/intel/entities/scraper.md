---
path: /Users/kurtistodd/houstontruckwreck-2/scraper.py
type: service
updated: 2026-01-20
status: active
---

# scraper.py

## Purpose

Primary web scraper for fetching heavy truck and hazmat incidents from Houston TranStar traffic management system. Attempts API endpoints first for structured data, falls back to HTML parsing if APIs fail. Filters incidents using keyword matching and regex patterns to identify relevant truck/hazmat events while excluding street-level incidents. Provides incident deduplication and severity scoring.

## Exports

- `TranStarScraper` - Main scraper class with methods:
  - `run_scrape_cycle()` - Complete scrape/filter/save workflow
  - `scrape_incidents()` - Fetch and parse incidents from TranStar
  - `is_relevant_incident(incident_data)` - Filter by truck/hazmat keywords
  - `save_new_incidents(incidents)` - Persist new incidents to database
  - `calculate_severity(description)` - Score incident urgency 1-5
- `test_scraper()` - Standalone test function

## Dependencies

- [[models]] - Incident model for persistence, Database for storage, Settings for stall toggle
- [[config]] - Base URL and configuration settings
- requests - HTTP client for API and HTML fetching
- beautifulsoup4 - HTML parsing for fallback scraping
- pytz - Central Time zone handling

## Used By

TBD

## Notes

API endpoints tried: /api/incidents/freeway, /api/incidents/stalls, /api/incidents/street, /api/incidents/closures. Uses browser-like User-Agent headers to avoid blocking. Respects the include_stalls setting to optionally filter out stall incidents. Location strings are normalized (Northbound -> NB, After -> @, etc.) for cleaner display.
