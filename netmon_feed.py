"""Private, bounded netmon feed. No upstream errors or secrets reach clients."""
from datetime import datetime, timezone
import math
import threading
import time
import requests


def epoch(value):
    try:
        if not isinstance(value, str) or len(value) > 40:
            return None
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.timestamp() if parsed.tzinfo else None
    except (ValueError, OverflowError):
        return None


def number(value, maximum):
    return value if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum else None


def sample(value):
    if not isinstance(value, dict):
        return None
    result = {'sampled_at': value.get('sampled_at') if epoch(value.get('sampled_at')) is not None else None,
              'collector_ok': value.get('collector_ok') is True}
    for key, maximum in [('internet_latency_ms', 60000), ('gateway_latency_ms', 60000), ('internet_loss_pct', 100), ('gateway_loss_pct', 100), ('devices_online', 65535), ('devices_seen', 65535)]:
        result[key] = number(value.get(key), maximum)
    return result


def sanitize(data):
    if not isinstance(data, dict) or data.get('ok') is not True or not isinstance(data.get('sources'), list) or len(data['sources']) > 100:
        raise ValueError('invalid feed')
    sources = []
    for s in data['sources']:
        if not isinstance(s, dict) or not isinstance(s.get('label'), str) or len(s['label']) > 80:
            raise ValueError('invalid source')
        speed = s.get('latest_speed')
        speed = {'download_mbps': number(speed.get('download_mbps'), 1000000), 'upload_mbps': number(speed.get('upload_mbps'), 1000000), 'speed_measured_at': speed.get('speed_measured_at') if epoch(speed.get('speed_measured_at')) is not None else None} if isinstance(speed, dict) else None
        history = s.get('history', [])
        if not isinstance(history, list) or len(history) > 289:
            raise ValueError('invalid history')
        sources.append({'label': s['label'], 'last_seen': s.get('last_seen') if epoch(s.get('last_seen')) is not None else None,
                        'latest_sample': sample(s.get('latest_sample')), 'latest_speed': speed,
                        'history': [{'sampled_at': h['sampled_at'], 'internet_latency_ms': h['internet_latency_ms'], 'gateway_latency_ms': h['gateway_latency_ms']} for h in (sample(x) for x in history) if h and h['sampled_at']]})
    return sources


class NetmonFeed:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.sources = None
        self.next_fetch = 0
        self.failed = False
        self.identity = None

    def fetch(self, config):
        try:
            return self._fetch(config)
        except Exception:
            # This optional feed must never take down the existing wall.
            return {'ok': False, 'configured': bool(config.NETMON_READ_TOKEN), 'error': 'Network feed unavailable', 'sources': []}

    def _fetch(self, config):
        if not config.NETMON_READ_TOKEN or not config.NETMON_STATUS_URL:
            return {'ok': False, 'configured': False}
        with self.lock:
            identity = (config.NETMON_STATUS_URL, config.NETMON_READ_TOKEN)
            if identity != self.identity:
                self.reset()
                self.identity = identity
            if time.monotonic() >= self.next_fetch:
                try:
                    response = requests.get(config.NETMON_STATUS_URL, headers={'Authorization': 'Bearer ' + config.NETMON_READ_TOKEN}, timeout=3, allow_redirects=False)
                    if response.status_code != 200 or len(response.content) > 2000000:
                        raise ValueError('invalid response')
                    self.sources = sanitize(response.json())
                    self.failed = False
                except Exception:
                    self.failed = True
                self.next_fetch = time.monotonic() + config.NETMON_CACHE_SECONDS
            now = time.time()
            sources = []
            for original in self.sources or []:
                s = dict(original)
                stamp = epoch((s['latest_sample'] or {}).get('sampled_at'))
                age = max(0, now - stamp) if stamp is not None and stamp <= now + 300 else None
                speed_stamp = epoch((s['latest_speed'] or {}).get('speed_measured_at'))
                speed_age = max(0, now - speed_stamp) if speed_stamp is not None and speed_stamp <= now + 300 else None
                state = 'OFFLINE' if age is None or age >= config.NETMON_OFFLINE_SECONDS else 'STALE' if self.failed or age >= config.NETMON_STALE_SECONDS or not s['latest_sample']['collector_ok'] else 'LIVE'
                s.update(state=state, sample_age_seconds=round(age) if age is not None else None,
                         speed_age_seconds=round(speed_age) if speed_age is not None else None,
                         speed_stale=speed_age is None or speed_age >= config.NETMON_SPEED_STALE_SECONDS)
                if speed_age is None:
                    s['latest_speed'] = None
                sources.append(s)
            result = {'ok': not self.failed, 'configured': True, 'stale': self.failed, 'server_time': datetime.fromtimestamp(now, timezone.utc).isoformat(), 'sources': sources}
            if self.failed:
                result['error'] = 'Network feed unavailable; showing last good data' if sources else 'Network feed unavailable'
            return result


feed = NetmonFeed()
