# Daily Summary Email Feature

## Overview
The Houston Traffic Monitor now automatically sends a comprehensive daily summary email at midnight (Central Time) to `ktoddllc1@gmail.com`. This email includes all wrecks and stalls that occurred during the day, with detailed location and time information, plus an attached CSV file for easy data analysis.

## Features

### 📧 Daily Email Summary
- **Schedule**: Automatically sent at midnight (12:00 AM Central Time)
- **Recipient**: ktoddllc1@gmail.com
- **Format**: HTML email with plain text fallback

### 📊 Summary Statistics
The email includes:
- Total incident count for the day
- Breakdown by type:
  - 🚗 Wrecks/Accidents
  - 🚛 Stalls
  - ☣️ Hazmat/Spills
  - ⚠️ Other incidents

### 📋 Detailed Incident List
Each incident includes:
- **Type icon** (visual indicator)
- **Location** (clickable Google Maps link)
- **Description**
- **Time of incident**
- **Severity level** (color-coded)

### 📎 CSV Attachment
When incidents occurred during the day, a CSV file is automatically attached with the following columns:
- Date
- Time
- Location
- Description
- Severity (High/Medium/Low)
- Scraped At (timestamp)

**CSV Filename Format**: `houston_traffic_incidents_YYYY-MM-DD.csv`

## Technical Implementation

### Files Modified
1. **email_service.py**
   - Added `generate_csv_data()` method for CSV generation
   - Added `create_daily_summary_html()` method for HTML email template
   - Added `send_daily_summary()` method to send the daily email

2. **app.py**
   - Added `send_daily_summary()` scheduled task function
   - Added cron job scheduled for midnight Central Time
   - Added `/test_daily_summary` route for manual testing

3. **templates/dashboard.html**
   - Added "Test Daily Summary" button to dashboard

### Scheduler Configuration
```python
scheduler.add_job(
    func=send_daily_summary,
    trigger=CronTrigger(hour=0, minute=0, timezone='America/Chicago'),
    id='daily_summary_job',
    name='Send daily summary email at midnight',
    replace_existing=True
)
```

## Testing the Feature

### Manual Test
You can test the daily summary feature without waiting until midnight:

1. Log in to the admin dashboard
2. Click the **"Test Daily Summary"** button in the top right
3. Check ktoddllc1@gmail.com for the summary email

### What the Test Does
- Fetches all incidents from the past 24 hours
- Generates the summary email with statistics
- Creates and attaches CSV file (if incidents exist)
- Sends to ktoddllc1@gmail.com

## Email Examples

### With Incidents
**Subject**: `📊 Daily Summary - January 7, 2026 - 15 Incidents`

The email will include:
- Summary statistics box showing counts by type
- Full table of all incidents with locations and times
- CSV file attachment

### No Incidents
**Subject**: `📊 Daily Summary - January 7, 2026 - No Incidents ✅`

The email will show:
- Green success message: "Great news! No incidents were reported today."
- No CSV attachment

## CSV File Format

Example CSV content:
```csv
Date,Time,Location,Description,Severity,Scraped At
2026-01-07,14:30,I-45 at Beltway 8,Semi-truck accident blocking left lane,Medium,2026-01-07 14:32:15
2026-01-07,15:45,US-59 near Downtown,Heavy truck stalled on shoulder,Low,2026-01-07 15:46:22
```

## Benefits

1. **Daily Overview**: Get a complete summary of the day's traffic incidents
2. **Data Analysis**: CSV file enables easy import to Excel, Google Sheets, or data analysis tools
3. **Historical Record**: Build a database of incidents over time
4. **Convenient Timing**: Midnight delivery means the previous day's data is ready first thing in the morning
5. **Professional Format**: Clean, organized HTML email with visual statistics

## Customization

To change the recipient email, modify the target email in `app.py`:

```python
def send_daily_summary():
    success = email_service.send_daily_summary(target_email="your_email@gmail.com")
```

Or modify the method signature in `email_service.py` to change the default:

```python
def send_daily_summary(self, target_email="your_email@gmail.com"):
```

## Logging

The system logs daily summary activities:
- `🕛 Running daily summary task...` - When the task starts
- `✅ Daily summary sent successfully` - When email is sent successfully
- `❌ Failed to send daily summary` - If there's an error

Check the application logs to monitor the daily summary feature.

## Requirements

The feature uses existing email configuration from the `.env` file:
- `EMAIL_USERNAME` - Gmail address
- `EMAIL_PASSWORD` - Gmail app password
- `EMAIL_FROM` - From address (defaults to EMAIL_USERNAME)

No additional configuration is required beyond the existing email setup.

## Support

For issues with the daily summary feature:
1. Check email configuration in `.env`
2. Review application logs for error messages
3. Use the "Test Daily Summary" button to manually trigger and diagnose issues
4. Verify that incidents are being detected and stored in the database
