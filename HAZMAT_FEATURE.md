# Hazmat-Only Alert System Feature

## Overview
The Houston Traffic Monitor now includes a separate alert system specifically for hazardous material (hazmat) spills and incidents. This allows you to manage a dedicated subscriber list that receives ONLY alerts for incidents containing "hazmat" or "spill" keywords.

## Features Implemented

### 1. Separate Subscriber Database
- Created `hazmat_subscribers` table in the database
- Independent from the regular subscribers list
- Each subscriber can be active/inactive
- Tracks subscription date

### 2. Hazmat-Specific Email Alerts
- **Distinctive Design**: Red-themed emails with hazmat warning symbols (☣️)
- **Filtered Content**: Only sends incidents containing "hazmat" or "spill" keywords
- **Critical Alert Branding**: Emphasizes the urgency of hazmat incidents
- **Automatic Detection**: System automatically identifies and separates hazmat incidents

### 3. Admin Management Interface
- New navigation menu item: "Hazmat Alerts" (☣️ icon)
- Dedicated page at `/hazmat_subscribers`
- Add/Remove/Toggle hazmat subscribers
- Visual distinction with red/danger theme
- Warning message explaining the hazmat-only nature

### 4. Automated Alert System
- Runs automatically during scheduled scrapes
- Sends regular alerts to all subscribers
- **Additionally** sends hazmat-specific alerts to hazmat subscribers
- No duplicate alerts if someone is on both lists
- Independent email sending with separate logging

## Default Subscribers

### Regular Subscribers (All Incidents)
The following emails are automatically added and will receive ALL incident alerts:
- ktoddizzle@icloud.com (Active)
- branhar01@gmail.com (Active)

These persist across redeployments and are always enabled by default.

### Hazmat Subscribers
Currently no default hazmat subscribers. You can add them through the admin panel at:
`Dashboard → Hazmat Alerts → Add New Hazmat Subscriber`

## How It Works

### When an Incident is Detected:
1. **Regular Alert Path**: 
   - Sends to all active regular subscribers
   - Includes ALL incident types (accidents, stalls, spills, etc.)

2. **Hazmat Alert Path**:
   - Filters incidents for "hazmat" or "spill" keywords
   - If hazmat incidents found:
     - Sends specialized hazmat alerts to hazmat subscribers only
     - Uses red-themed email template with hazmat branding
     - Emphasizes critical nature of the incident

### Email Differences:

**Regular Alerts:**
- Blue theme
- Subject: "🚛 Heavy Truck Incident Alert - Houston"
- Contains all types of incidents
- Standard priority indicators

**Hazmat Alerts:**
- Red theme with hazmat symbols
- Subject: "☣️ HAZMAT ALERT: X Spill/Hazmat Incident(s) in Houston!"
- Only hazmat/spill incidents
- "CRITICAL" and "Immediate attention required" messaging
- Footer notes: "You are receiving this because you subscribed to hazmat-only alerts"

## Usage Guide

### Adding Hazmat Subscribers
1. Log into admin dashboard
2. Click "Hazmat Alerts" in sidebar
3. Enter email address
4. Click "Add Hazmat Subscriber"

### Managing Subscribers
- **Deactivate**: Temporarily disable alerts without removing
- **Activate**: Re-enable a deactivated subscriber
- **Remove**: Permanently delete from hazmat list

### Subscriber Lists are Independent
- Someone can be on regular list only
- Someone can be on hazmat list only
- Someone can be on BOTH lists (will receive both types of alerts)

## Technical Implementation

### Files Modified:
1. **models.py**: Added `hazmat_subscribers` table and `HazmatSubscriber` class
2. **email_service.py**: Added `send_hazmat_alert()` method with filtering logic
3. **app.py**: Added routes for hazmat subscriber management + integrated into scraper
4. **templates/hazmat_subscribers.html**: New admin interface (created)
5. **templates/base.html**: Added navigation menu item

### Database Schema:
```sql
CREATE TABLE hazmat_subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### API Endpoints:
- `GET /hazmat_subscribers` - View hazmat subscriber management page
- `POST /add_hazmat_subscriber` - Add new hazmat subscriber
- `POST /remove_hazmat_subscriber` - Remove hazmat subscriber
- `POST /toggle_hazmat_subscriber` - Toggle active status

## Benefits

1. **Specialized Monitoring**: Organizations/individuals can focus only on hazmat incidents
2. **Reduced Alert Fatigue**: Hazmat subscribers don't receive routine traffic alerts
3. **Faster Response**: Critical hazmat alerts stand out with distinctive red branding
4. **Flexibility**: Maintain both general and specialized subscriber lists
5. **No Duplication**: System prevents sending duplicate alerts to same email

## Testing

To test the hazmat alert system:
1. Add a test email to hazmat subscribers
2. Wait for a hazmat/spill incident to be detected
3. Or manually trigger scrape when hazmat incident is on Houston TranStar

The system will automatically:
- Filter for hazmat/spill keywords
- Send specialized red-themed alert
- Log successful delivery

## Future Enhancements (Optional)

Potential additions:
- Daily hazmat-only summary emails
- Text message alerts for hazmat incidents
- Geographic filtering (specific areas only)
- Severity-based filtering for hazmat alerts
- Integration with emergency response systems
