"""Conservative TranStar identity and notification-change classification.

The HTML feed exposes a location and a reported clock time, not an event ID.
Lane details are mutable. Do not use map coordinates as an event identifier.
"""
from datetime import datetime, timedelta
import re

import pytz

CENTRAL = pytz.timezone('America/Chicago')


def normalize(text):
    return ' '.join((text or '').casefold().split())


def location_key(location):
    text = normalize(location)
    text = re.sub(r'\b(north|south|east|west)bound\b',
                  lambda m: m.group(1)[0] + 'b', text)
    text = re.sub(r'\bi-(\d+)\b', r'ih-\1', text)
    text = re.sub(r'\bat\b', '@', text)
    return re.sub(r'\s*@\s*', ' @ ', text).strip()


def reported_clock(status):
    """Return a validated source time, never the current scrape time."""
    match = re.search(r'(?<!\d)(\d{1,2}:\d{2})\s*([ap]m)?\b', status or '', re.I)
    if not match:
        return None
    try:
        value = match.group(1)
        if match.group(2):
            value += ' ' + match.group(2).upper()
        clock = datetime.strptime(value, '%I:%M %p' if match.group(2) else '%H:%M')
        return clock.strftime('%H:%M')
    except ValueError:
        return None


def occurrence_key(status, observed_at):
    """Resolve time-only rows to a Houston calendar date, including midnight.

Keep different source times separate rather than guessing that they are updates.
Full source dates take precedence over the inferred date.
"""
    clock = reported_clock(status)
    if clock is None:
        return None
    now = observed_at.astimezone(CENTRAL)
    day = now.date()
    explicit = re.search(r'\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b', status or '')
    if explicit:
        value = explicit.group(1)
        try:
            day = datetime.strptime(value, '%Y-%m-%d' if '-' in value else '%m/%d/%Y').date()
        except ValueError:
            return None
    elif 'yesterday' in normalize(status):
        day -= timedelta(days=1)
    elif 'today' not in normalize(status):
        candidate = datetime.combine(day, datetime.strptime(clock, '%H:%M').time())
        if candidate > now.replace(tzinfo=None) + timedelta(minutes=5):
            day -= timedelta(days=1)
    return f'{day.isoformat()}T{clock}'


# Additions to these flags warrant another notification for the SAME record.
# Lane counts/positions, verification wording, and description order do not.
PRIORITY_PATTERNS = (
    r'\b(?:accident|crash|collision|wreck)\b',
    r'\b(?:hazmat|hazardous material\w*|spill\w*|leak\w*)\b',
    r'\b(?:rollover|overturned|jackknife\w*)\b',
    r'\b(?:fire|burning)\b',
    r'\binjur\w*\b',
    r'\b(?:multiple vehicles|multi-vehicle|pile-up)\b',
    r'\blost (?:load|cargo)\b',
    r'\bfatal\w*\b',
)


def priority_flags(description):
    return sum(1 << i for i, pattern in enumerate(PRIORITY_PATTERNS)
               if re.search(pattern, description or '', re.I))


def core_description(description):
    """Strip only standalone lane cells when matching a pre-fix database row."""
    lane = re.compile(
        r'^(?:\d+\s+)?(?:(?:left|right|center|middle|alternate|all|frontage road|main)\s+)*'
        r'(?:lane(?:\(s\)|s)?|shoulder|exit ramp|entrance ramp)(?:\s+(?:blocked|closed))?$')
    parts = [normalize(p).strip('.') for p in description.split(',')]
    return ','.join(sorted(p for p in parts if p and not lane.fullmatch(p)))
