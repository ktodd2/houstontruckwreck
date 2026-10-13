"""Isolated tests: no production DB, jobs, credentials, or outbound requests."""
import atexit
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

TMP = tempfile.TemporaryDirectory()
with patch.dict(os.environ, {'ADMIN_USERNAME': 'test-admin', 'ADMIN_PASSWORD': 'test-only-password'}, clear=True), patch('dotenv.load_dotenv', return_value=False):
    from config import Config
    Config.DATABASE_PATH = str(Path(TMP.name) / 'netmon-tests.db')
    with patch('apscheduler.schedulers.background.BackgroundScheduler.start'), patch('atexit.register'):
        import app as wall
from netmon_feed import feed
atexit.register(TMP.cleanup)


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def payload(age=10, speed_age=600, now=2000000000):
    sample = {'sampled_at': iso(now-age), 'collector_ok': True, 'internet_latency_ms': 4.4, 'internet_loss_pct': 0, 'gateway_latency_ms': .5, 'gateway_loss_pct': 0, 'devices_online': 8, 'devices_seen': 9}
    return {'ok': True, 'server_time': iso(1), 'sources': [{'label': 'Home Mac', 'last_seen': iso(now), 'latest_sample': sample, 'latest_speed': {'download_mbps': 6702, 'upload_mbps': 1853, 'speed_measured_at': iso(now-speed_age)}, 'history': [sample]}]}


class NetmonTests(unittest.TestCase):
    def setUp(self):
        feed.reset()
        self.patches = [patch.object(Config, 'NETMON_READ_TOKEN', 'test-only-read-token'), patch.object(Config, 'NETMON_STATUS_URL', 'https://example.invalid/netmon-status'), patch('netmon_feed.time.time', return_value=2000000000), patch('app._fetch_store_stats', return_value={'ok': True, 'unfilled': []}), patch('app._load_briefings', return_value=[]), patch('requests.get')]
        value = Mock()
        for p in self.patches:
            value = p.start()
            self.addCleanup(p.stop)
        self.get = value
        self.get.return_value = Mock(status_code=200, content=b'{}', json=lambda: payload())
        self.client = wall.app.test_client()
        with self.client.session_transaction() as session:
            session['_user_id'] = Config.DEFAULT_ADMIN_USERNAME
            session['_fresh'] = True

    def live(self):
        response = self.client.get('/api/live')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(set(['generated_at','generated_label','window_hours','counts','total_incidents','incidents','stats','scraper','logs','briefings','store','netmon']) <= set(data))
        self.assertNotIn('test-only-read-token', response.get_data(as_text=True))
        return data['netmon']

    def test_unauthenticated(self):
        c = wall.app.test_client()
        for path in ('/live', '/api/live'):
            r = c.get(path)
            self.assertEqual(r.status_code, 302)
            self.assertIn('/login', r.location)
            self.assertNotIn('netmon', r.get_data(as_text=True))
        self.get.assert_not_called()

    def test_live_and_cache(self):
        data = self.live()
        self.assertEqual(data['sources'][0]['state'], 'LIVE')
        self.assertEqual(data['sources'][0]['sample_age_seconds'], 10)
        self.assertEqual(data['sources'][0]['speed_age_seconds'], 600)
        self.live()
        self.assertEqual(self.get.call_count, 1)
        self.assertEqual(self.get.call_args.kwargs['timeout'], 3)
        self.assertFalse(self.get.call_args.kwargs['allow_redirects'])

    def test_thresholds(self):
        for age, expected in [(119,'LIVE'), (120,'STALE'), (299,'STALE'), (300,'OFFLINE')]:
            with self.subTest(age=age):
                feed.reset()
                self.get.return_value.json = lambda: payload(age=age, speed_age=7200)
                s = self.live()['sources'][0]
                self.assertEqual(s['state'], expected)
                self.assertTrue(s['speed_stale'])

    def test_unconfigured(self):
        with patch.object(Config, 'NETMON_READ_TOKEN', None):
            self.assertEqual(self.live(), {'ok': False, 'configured': False})
        self.get.assert_not_called()

    def test_failure_and_last_good(self):
        self.live()
        feed.next_fetch = 0
        self.get.side_effect = RuntimeError('private URL test-only-read-token')
        d = self.live()
        self.assertFalse(d['ok'])
        self.assertTrue(d['stale'])
        self.assertEqual(d['sources'][0]['state'], 'STALE')
        self.assertNotIn('private URL', json.dumps(d))
        feed.reset()
        self.assertEqual(self.live()['sources'], [])

    def test_invalid_upstream(self):
        for bad in [None, [], {'ok': True, 'sources': 'bad'}, {'ok': True, 'sources': [None]}]:
            feed.reset()
            self.get.return_value.json = lambda: bad
            self.assertFalse(self.live()['ok'])

    def test_whitelist_and_nulls(self):
        p = payload()
        p['token'] = 'private-secret'
        p['sources'][0]['source_key'] = 'private-source'
        p['sources'][0]['latest_sample']['mac'] = 'private-mac'
        p['sources'][0]['latest_sample']['internet_latency_ms'] = None
        self.get.return_value.json = lambda: p
        d = self.live()
        self.assertNotIn('private-', json.dumps(d))
        self.assertIsNone(d['sources'][0]['latest_sample']['internet_latency_ms'])

    def test_html_and_tow_exclusion(self):
        html = self.client.get('/live').get_data(as_text=True)
        self.assertIn('Home network', html)
        self.assertNotIn('test-only-read-token', html)
        for path in ('/tow', '/api/tow'):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200)
            self.assertNotIn('netmon', r.get_data(as_text=True).lower())
            self.assertNotIn('Home network', r.get_data(as_text=True))
        self.get.assert_not_called()

    def test_viewer_only_cannot_read_live(self):
        with patch.object(Config, 'WALL_USERNAME', 'viewer'), patch.object(Config, 'WALL_PASSWORD', 'test-viewer-password'):
            c = wall.app.test_client()
            c.post('/tow/login', data={'username': 'viewer', 'password': 'test-viewer-password'})
            self.assertEqual(c.get('/api/tow').status_code, 200)
            self.assertEqual(c.get('/api/live').status_code, 302)
            self.get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
