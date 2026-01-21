---
path: /Users/kurtistodd/houstontruckwreck-2/selenium_scraper.py
type: service
updated: 2026-01-20
status: active
---

# selenium_scraper.py

## Purpose

Browser-based web scraper using Selenium WebDriver for fetching traffic incidents from Houston TranStar. Designed as an alternative to the requests-based scrapers when JavaScript rendering is required. Uses headless Chrome to load pages, interact with tab navigation (Stalls, Freeway Incidents), and scrape dynamically-loaded table content. Provides the same filtering and severity logic as other scrapers.

## Exports

- `SeleniumTranStarScraper` - Browser-based scraper class with methods:
  - `run_scrape_cycle()` - Complete scrape/filter/save workflow
  - `scrape_incidents()` - Launch browser, navigate tabs, extract data
  - `setup_driver()` - Configure headless Chrome with appropriate options
  - `scrape_table_section(section_name)` - Extract incidents from visible table
  - `is_relevant_incident(location, description)` - Filter by truck/hazmat keywords
  - `save_new_incidents(incidents)` - Persist new incidents to database
  - `calculate_severity(description)` - Score incident urgency 1-5
- `test_selenium_scraper()` - Standalone test function

## Dependencies

- [[models]] - Incident model for persistence, Database for storage, Settings for stall toggle
- [[config]] - Configuration settings
- selenium - Browser automation framework
- selenium.webdriver - Chrome WebDriver for headless browsing

## Used By

TBD

## Notes

Requires Chrome/Chromium and ChromeDriver installed on the system. Uses headless mode with window size 1920x1080. Explicitly clicks on Stalls and Freeway Incidents tabs to trigger dynamic content loading. Waits up to 20 seconds for page load plus 5 second delays for JavaScript execution. More resource-intensive than requests-based scrapers but handles JS-rendered content.
