"""Offline regressions: temporary databases, synthetic credentials, mocked SMTP.

Run: python -m unittest -v test_incident_identity test_netmon
The fixture reproduces the verified Nov 6, 2026 emails and Render log rows.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

with patch.dict(os.environ, {}, clear=True), patch('dotenv.load_dotenv', return_value=False):
    from config import Config
    from models import Database, Incident, SentAlert, Settings, Subscriber, HazmatSubscriber
    from scraper import TranStarScraper
    from email_service import EmailService
from incident_identity import occurrence_key

FIXTURE = json.loads((Path(__file__).parent / 'tests/fixtures/november_6_lane_update.json').read_text())


class IncidentIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for p in [patch.object(Config, 'DATABASE_PATH', str(Path(self.tmp.name) / 'test.db')),
                  patch.object(Config, 'EMAIL_USERNAME', 'sender@example.invalid'),
                  patch.object(Config, 'EMAIL_PASSWORD', 'test-only'),
                  patch.object(Config, 'EMAIL_FROM', 'sender@example.invalid'),
                  patch('requests.sessions.Session.request', side_effect=AssertionError('Network forbidden')),
                  patch('socket.create_connection', side_effect=AssertionError('Network forbidden'))]:
            p.start()
            self.addCleanup(p.stop)
        with redirect_stdout(io.StringIO()), patch.object(EmailService, '_load_logo', return_value=''):
            self.scraper = TranStarScraper()
            self.email = EmailService()
        self.db = self.scraper.db
        self.smtp_patch = patch('email_service.smtplib.SMTP')
        self.smtp = self.smtp_patch.start().return_value.__enter__.return_value
        self.addCleanup(self.smtp_patch.stop)

    def observation(self, index=0, **overrides):
        values = dict(FIXTURE[index], **overrides)
        cells = [values['location'], values['description'], values['lanes'], values['status'], 'Map']
        with patch.object(self.scraper, 'get_central_time_now',
                          return_value=datetime.fromisoformat(values['observed_at'])):
            return self.scraper.create_incident_from_html_row(cells, 'stalls')

    def rows(self):
        with self.db.get_connection() as conn:
            return list(conn.execute('SELECT * FROM incidents ORDER BY id'))

    def dispatch(self, incidents):
        queued = self.scraper.save_new_incidents(incidents)
        if queued:
            self.email.send_alert(queued)
            self.email.send_hazmat_alert(queued)
        return queued

    def test_verified_november_6_replay_sends_once_and_summary_counts_once(self):
        first = self.observation()
        queued = self.dispatch([first])
        second = self.observation(1)
        self.assertEqual(first.incident_hash, second.incident_hash)
        self.assertEqual(len(queued), 1)
        self.assertEqual(self.dispatch([second]), [])
        self.smtp.send_message.assert_called_once()
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['description'], 'Heavy Truck, Stall, 2 Center Lanes')
        self.assertEqual(rows[0]['incident_time'], '6:39 PM')
        self.assertEqual(rows[0]['scraped_at'], '2026-11-07 00:40:49')
        self.assertEqual(rows[0]['last_seen_at'], '2026-11-07 00:41:49')
        self.assertTrue(Incident.is_already_sent(self.db, first.incident_hash))
        # Replay the real summary sender with the fixture's day's records.
        with patch.object(Incident, 'get_recent', return_value=rows):
            self.assertTrue(self.email.send_daily_summary(target_email='summary@example.invalid'))
        summary = self.smtp.send_message.call_args.args[0]
        self.assertIn('1 Incident', summary['Subject'])
        self.assertEqual(len(list(csv.reader(io.StringIO(self.email.generate_csv_data(rows))))), 2)

    def test_html_scrape_workflow_keeps_source_identity(self):
        for index, values in enumerate(FIXTURE):
            html = '<h2>Stalls</h2><table><tr>' + ''.join('<td>' + values[k] + '</td>'
                    for k in ['location', 'description', 'lanes', 'status']) + '</tr></table>'
            response = Mock(content=html.encode())
            with patch.object(self.scraper.session, 'get', return_value=response), patch.object(
                    self.scraper, 'get_central_time_now', return_value=datetime.fromisoformat(values['observed_at'])):
                queued = self.scraper.run_scrape_cycle()
            self.assertEqual(len(queued), 1 if index == 0 else 0)
        self.assertEqual(len(self.rows()), 1)

    def test_real_scheduled_callback_sends_only_one_alert_for_the_two_polls(self):
        with patch('apscheduler.schedulers.background.BackgroundScheduler.start'), patch('atexit.register'):
            import app as monitor
        polls = [[self.observation()], [self.observation(1)]]
        with patch.object(monitor, 'scraper', self.scraper), patch.object(monitor, 'email_service', self.email), \
                patch.object(self.scraper, 'scrape_incidents', side_effect=polls):
            monitor.scheduled_scrape()
            monitor.scheduled_scrape()
        self.smtp.send_message.assert_called_once()
        self.assertEqual(len(self.rows()), 1)

    def test_different_report_times_dates_locations_directions_and_relations_are_new(self):
        values = [self.observation(), self.observation(status='Verified at 6:40 PM'),
                  self.observation(observed_at='2026-11-07T18:40:49-06:00'),
                  self.observation(location='IH-10 Katy Eastbound At Dairy Ashford Rd'),
                  self.observation(location='IH-10 Katy Westbound At Kirkwood Rd'),
                  self.observation(location='IH-10 Katy Westbound Before Dairy Ashford Rd'),
                  self.observation(location='IH-10 Katy Westbound After Dairy Ashford Rd')]
        self.assertEqual(len(self.scraper.save_new_incidents(values)), len(values))
        self.assertEqual(len(self.rows()), len(values))

    def test_case_whitespace_lane_and_verification_updates_do_not_alert(self):
        self.dispatch([self.observation()])
        updates = [self.observation(1, status='Detected at 18:39'),
                   self.observation(location='ih-10   katy westbound at dairy ashford rd',
                                    description='STALL, heavy truck', status='Updated at 06:39PM'),
                   self.observation(lanes='All Lanes Blocked')]
        self.assertEqual(self.dispatch(updates), [])
        self.smtp.send_message.assert_called_once()
        self.assertEqual(len(self.rows()), 1)

    def test_accident_then_hazmat_are_updates_and_reach_both_recipient_groups(self):
        original = self.dispatch([self.observation()])[0][1]
        self.smtp.send_message.reset_mock()
        accident = self.dispatch([self.observation(description='Heavy Truck, Stall, Accident')])
        self.assertEqual(accident[0][1], original)
        self.assertTrue(accident[0][0].is_update)
        self.assertEqual(self.smtp.send_message.call_count, 2)
        messages = [c.args[0] for c in self.smtp.send_message.call_args_list]
        recipients = {part.strip() for msg in messages for part in msg['To'].split(',')}
        self.assertEqual(recipients, set(Subscriber.get_all_active(self.db)))
        self.assertTrue(all('UPDATE:' in m['Subject'] and 'ACCIDENT' in m['Subject'] for m in messages))
        self.smtp.send_message.reset_mock()
        hazmat = self.dispatch([self.observation(description='Heavy Truck, Stall, Accident, Hazmat Spill')])
        self.assertEqual(hazmat[0][1], original)
        self.assertEqual(self.smtp.send_message.call_count, 3)  # two regular groups + hazmat list
        self.assertIn('HAZMAT', self.smtp.send_message.call_args.args[0]['Subject'])
        self.assertEqual(self.dispatch([self.observation(1, description='Heavy Truck, Stall, Accident, Hazmat Spill')]), [])
        self.assertEqual(len(self.rows()), 1)

    def test_priority_flicker_does_not_repeat_an_already_seen_escalation(self):
        self.dispatch([self.observation()])
        self.assertEqual(len(self.dispatch([self.observation(description='Heavy Truck, Accident')])), 1)
        self.assertEqual(self.dispatch([self.observation()]), [])
        self.assertEqual(self.dispatch([self.observation(description='Heavy Truck, Accident')]), [])

    def test_other_important_new_facts_are_not_suppressed(self):
        self.scraper.save_new_incidents([self.observation()])
        for keyword in ['Accident', 'Hazmat Spill', 'Rollover', 'Fire', 'Injuries', 'Multiple vehicles', 'Lost load', 'Fatality']:
            with self.subTest(keyword=keyword):
                result = self.scraper.save_new_incidents([self.observation(description='Heavy Truck, ' + keyword)])
                self.assertEqual(len(result), 1)
                self.assertTrue(result[0][0].is_update)
        self.assertEqual(len(self.rows()), 1)

    def test_same_poll_updates_coalesce_and_keep_latest_lanes(self):
        queued = self.dispatch([self.observation(), self.observation(1)])
        self.assertEqual(len(queued), 1)
        self.assertIn('2 Center Lanes', queued[0][0].description)
        self.assertFalse(queued[0][0].is_update)
        self.smtp.send_message.assert_called_once()

    def test_same_poll_cannot_drop_a_later_or_earlier_hazmat_observation(self):
        for reverse in [False, True]:
            with self.subTest(reverse=reverse):
                stamp = '6:39 PM' if reverse else '6:40 PM'
                items = [self.observation(status=stamp),
                         self.observation(description='Heavy Truck, Accident, Hazmat Spill', status=stamp)]
                if reverse:
                    items.reverse()
                items = self.scraper.remove_duplicate_incidents(items)
                self.assertEqual(len(items), 2)
                queued = self.dispatch(items)
                self.assertEqual(len(queued), 1)
                self.assertIn('Hazmat Spill', queued[0][0].description)
                self.assertIn('HAZMAT', self.smtp.send_message.call_args.args[0]['Subject'])

    def test_midnight_does_not_change_identity(self):
        first = self.observation(status='Verified at 11:59 PM', observed_at='2026-11-06T23:59:30-06:00')
        after = self.observation(1, status='Verified at 11:59 PM', observed_at='2026-11-07T00:01:00-06:00')
        self.assertEqual(first.incident_hash, after.incident_hash)
        self.assertEqual(len(self.dispatch([first])), 1)
        self.assertEqual(self.dispatch([after]), [])

    def test_explicit_source_dates_and_yesterday(self):
        now = datetime.fromisoformat('2026-11-07T18:45:00-06:00')
        expected = '2026-11-06T18:39'
        for status in ['11/6/2026 at 6:39 PM', '2026-11-06 18:39', 'Yesterday at 6:39 PM']:
            self.assertEqual(occurrence_key(status, now), expected)

    def test_missing_and_invalid_times_do_not_fuzzy_merge_different_rows(self):
        for status in ['', 'Verified', 'Verified at 25:99', 'Verified at 13:39 PM']:
            with self.subTest(status=status):
                first, second = self.observation(status=status), self.observation(1, status=status)
                self.assertIsNone(first.occurrence)
                self.assertNotEqual(first.incident_hash, second.incident_hash)
        self.assertIsNone(occurrence_key('2026-13-40 at 6:39 PM', datetime.fromisoformat(FIXTURE[0]['observed_at'])))

    def test_restart_with_existing_database_does_not_realert(self):
        self.dispatch([self.observation()])
        with redirect_stdout(io.StringIO()):
            self.scraper = TranStarScraper()
        self.assertEqual(self.dispatch([self.observation(1)]), [])
        self.smtp.send_message.assert_called_once()

    def insert_legacy(self, description='Heavy Truck, Stall, Center Lane', time='6:39 PM', seen='2026-11-07 00:40:49'):
        location = 'IH-10 Katy WB @ Dairy Ashford Rd'
        old_hash = hashlib.md5(f'{location.lower()}:{description.lower()[:100]}'.encode()).hexdigest()
        with self.db.get_connection() as conn:
            row_id = conn.execute('''INSERT INTO incidents (incident_hash, location, description, incident_time, scraped_at)
                                  VALUES (?, ?, ?, ?, ?)''', (old_hash, location, description, time, seen)).lastrowid
        SentAlert.mark_sent(self.db, row_id)
        return row_id, old_hash

    def test_legacy_row_is_adopted_without_realert_or_changing_sent_history(self):
        row_id, old_hash = self.insert_legacy()
        self.assertEqual(self.dispatch([self.observation(1)]), [])
        row = self.rows()[0]
        self.assertEqual(row['id'], row_id)
        self.assertEqual(row['incident_hash'], old_hash)
        self.assertIsNotNone(row['identity_key'])
        self.assertTrue(Incident.is_already_sent(self.db, old_hash))
        self.assertEqual(self.dispatch([self.observation()]), [])
        self.smtp.send_message.assert_not_called()

    def test_legacy_other_day_or_time_is_not_suppressed(self):
        self.insert_legacy(time='5:39 PM')
        self.insert_legacy(description='Heavy Truck, Stall, Right Lane', seen='2026-11-06 00:40:49')
        self.assertEqual(len(self.dispatch([self.observation()])), 1)
        self.assertEqual(len(self.rows()), 3)

    def test_ambiguous_legacy_matches_are_left_intact(self):
        self.insert_legacy()
        self.insert_legacy(description='Heavy Truck, Stall, Right Shoulder')
        self.assertEqual(len(self.dispatch([self.observation(1)])), 1)
        self.assertEqual(len(self.rows()), 3)

    def test_schema_migration_is_additive_and_repeatable(self):
        legacy_path = str(Path(self.tmp.name) / 'legacy.db')
        with sqlite3.connect(legacy_path) as conn:
            conn.execute('''CREATE TABLE incidents (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         incident_hash TEXT UNIQUE NOT NULL, location TEXT NOT NULL,
                         description TEXT NOT NULL, incident_time TEXT, scraped_at TIMESTAMP
                         DEFAULT CURRENT_TIMESTAMP, severity INTEGER DEFAULT 1)''')
            conn.execute("INSERT INTO incidents (incident_hash, location, description) VALUES ('original', 'road', 'truck')")
        with redirect_stdout(io.StringIO()):
            migrated = Database(legacy_path)
            Database(legacy_path)
        with migrated.get_connection() as conn:
            row = conn.execute('SELECT * FROM incidents').fetchone()
        self.assertEqual(row['id'], 1)
        self.assertEqual(row['incident_hash'], 'original')
        self.assertIsNone(row['identity_key'])
        self.assertIn('last_seen_at', row.keys())

    def test_concurrent_observations_queue_once(self):
        observations = [self.observation(), self.observation(1)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(lambda inc: inc.save(self.db), observations))
        self.assertEqual(sum(i is not None for i in ids), 1)
        self.assertEqual(len(self.rows()), 1)

    def test_concurrent_escalations_queue_once(self):
        self.observation().save(self.db)
        observations = [self.observation(description='Heavy Truck, Accident') for _ in range(2)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(lambda inc: inc.save(self.db), observations))
        self.assertEqual(sum(i is not None for i in ids), 1)

    def test_stall_preferences_and_configuration_are_preserved(self):
        original = Subscriber.get_all_active_with_stalls(self.db)
        hazmat = HazmatSubscriber.get_all_active(self.db)
        interval, limit = Config.SCRAPE_INTERVAL, Config.MAX_ALERTS_PER_HOUR
        self.dispatch([self.observation()])
        msg = self.smtp.send_message.call_args.args[0]
        self.assertEqual(set(msg['To'].split(', ')), {email for email, wants in original if wants})
        self.dispatch([self.observation(1)])
        self.assertEqual(Subscriber.get_all_active_with_stalls(self.db), original)
        self.assertEqual(HazmatSubscriber.get_all_active(self.db), hazmat)
        self.assertEqual((Config.SCRAPE_INTERVAL, Config.MAX_ALERTS_PER_HOUR), (interval, limit))

    def test_disabled_stalls_do_not_hide_accident_or_hazmat(self):
        Settings.set_include_stalls(self.db, False)
        self.assertFalse(self.scraper.is_relevant_incident('Heavy Truck, Stall'))
        self.assertTrue(self.scraper.is_relevant_incident('Heavy Truck, Stall, Accident'))
        self.assertTrue(self.scraper.is_relevant_incident('Heavy Truck, Stall, Hazmat Spill'))
        self.assertFalse(Settings.get_include_stalls(self.db))

    def test_existing_regular_alert_rate_limit_remains_enforced(self):
        queued = self.scraper.save_new_incidents([self.observation()])
        with patch.object(SentAlert, 'get_recent_count', return_value=Config.MAX_ALERTS_PER_HOUR):
            self.assertFalse(self.email.send_alert(queued))
        self.smtp.send_message.assert_not_called()


if __name__ == '__main__':
    unittest.main()
