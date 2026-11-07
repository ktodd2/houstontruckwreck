# Incident deduplication correction — November 7, 2026

Status: proposed for review only. No production database changes, live test emails,
merge, or deployment were performed during development.

## Confirmed cause

Render's live deployment is commit `4fdff4d052d3dbdfb38b94d4e0bc23e66ad51d38`,
which also matches the inspected `main` branch. The service starts with
`python3 start_app.py`, imports `app.py`, and schedules `TranStarScraper` once a
minute. The observed November 6 log cadence confirms the one-minute interval.

The old parser appends the lanes cell to `description`. The old incident hash
uses location and the first 100 description characters, excluding neither lanes
nor other changing details. It also omits occurrence time entirely. Each new
hash creates a database row, which enters the email pipeline. The daily summary
counts database rows, so it counts those updates again.

The two supplied emails were read and the production logs independently show:

| Houston time, November 6 | Source report time | Description | Observed production action |
| --- | --- | --- | --- |
| 6:40:49 PM CST | 6:39 PM | Heavy Truck, Stall, Center Lane | New record; regular alert successfully sent |
| 6:41:49 PM CST | 6:39 PM | Heavy Truck, Stall, 2 Center Lanes | Another new record; another regular alert successfully sent |

Both rows refer to IH-10 Katy westbound at Dairy Ashford Road. The daily summary
also contains both as entries #5 and #6. This is a confirmed deployed-code bug,
not only a hypothesis from the repository documentation.

## Proposed behavior

- Timed observations use a key comprising the source, normalized source location,
  and source occurrence date/time. Lanes and description wording are not identity.
- Preserve the raw location for matching: direction and Before/At/After/Near are
  not collapsed into one position, even though the existing display formatter
  continues to use `@`.
- Update the existing description, severity, map link and last-seen time while
  preserving its row ID and original `scraped_at`. Thus one evolving event remains
  one summary row and lane changes do not trigger another alert.
- Different source times, dates, directions, locations and positional relationships
  remain different events, including the same stall description later in the day.
- New accident, hazmat/spill/leak, rollover/jackknife, fire, injury, fatality,
  multi-vehicle or lost-load information triggers an explicitly labeled update
  on the same record. Each newly observed category triggers at most once per event.
  A lane-only severity increase does not trigger an update.
- An accident or hazmat description that still contains the word `Stall` is not
  discarded by the pure-stall filters. Existing stall opt-outs remain in force
  for ordinary stalls; no recipient or preference is changed.
- Keep meaningful changes seen in the same polling batch and combine them into
  one notification item per incident. Serialize database writes to prevent
  concurrent polls from both creating or escalating the same event.

The database migration adds `identity_key`, `alert_flags`, `last_seen_at`, and a
unique identity index. It does not delete records or rewrite historical IDs or
sent-alert links. On observation, a single unambiguous legacy row with matching
location, occurrence and lane-independent description is adopted without replay.
Existing duplicate historical rows are not automatically merged or deleted.

## Verification

All tests used temporary SQLite files, synthetic credentials and mocked SMTP.
Outbound network access and scheduler startup were blocked in the test harness.
The fixture contains the two verified source rows and alert-generation times;
the HTML structure used for parser tests is synthetic, not an archived page.

| Check | Result |
| --- | --- |
| Unmodified source replay | 2 queued alerts, 2 incident rows |
| Corrected November 6 replay | 1 regular email, 1 incident row, latest two-center-lane details |
| Real scheduled callback, two polling cycles | 1 regular email |
| Daily summary / CSV replay | 1 incident in subject; 1 CSV data row |
| New deduplication regression tests | 23 passed |
| Existing `test_netmon` dashboard tests | 9 passed |
| Existing `test_system` smoke checks with isolated DB/network/scheduler | 5 of 5 passed |
| Python compilation and `git diff --check` | Passed |

Run the automated regression suites after installing `requirements.txt`:

```sh
python -m unittest -v test_incident_identity test_netmon
python -m compileall -q app.py models.py scraper.py email_service.py incident_identity.py test_incident_identity.py
git diff --check
```

Coverage includes distinct times/days/locations/directions/positions, casing and
whitespace, 12/24-hour notation, midnight, explicit dates, missing/invalid times,
accident then hazmat escalation, safety-category flicker, same-poll observations
in both orders, legacy adoption, ambiguous legacy records, additive repeatable
migration, database reuse after restart, concurrent saves and escalations,
subscriber routing, disabled-stall behavior and the existing regular-email limit.

Polling, midnight-summary scheduling, SMTP configuration, subscriber lists,
regular/hazmat delivery channels and configured frequency limits are unchanged.
The existing system can intentionally send both a regular alert and a dedicated
hazmat alert for a hazmat event; this change preserves that behavior.

## Boundaries and deployment considerations

- The HTML rows used by this scraper do not provide a stable event ID. The map
  link represents coordinates, not identity. Two separate events with exactly
  the same source location and reported minute cannot reliably be distinguished.
  A changed reported time is deliberately treated as new, rather than using a
  fuzzy geographic or time-window suppression rule.
- For time-only source rows, the Houston calendar date is inferred, including
  just after midnight. A long-running event still present at the same clock time
  on a later day can be treated as new. Full dates, when supplied, take precedence.
- Missing or invalid source times retain a conservative description-based daily
  fallback. Different descriptions are not merged by location alone; duplicate
  lane updates can still occur for these ambiguous rows. Identical undated rows
  cannot distinguish repeated events during the same day.
- Legacy rows with ambiguous matches or a lost Before/After/Near relationship
  are left intact; an incoming event may alert once when it cannot be safely
  associated with old state. The historical November 6 summary is not rewritten.
- Existing SMTP failure, partial-delivery and rate-limit retry behavior is not
  redesigned into an outbox. As before, successful persistence can precede a
  failed send. The tests establish enqueueing/routing behavior, not guaranteed
  delivery or exactly-once SMTP across a process crash.
- `Config.DATABASE_PATH` currently selects `/tmp/database.db` on Render; the
  checked-in deployment configuration explicitly has no persistent disk. Losing
  that database loses deduplication history and can re-alert active incidents.
  Restart tests cover reuse of the same database, not loss of that database.
- Before an approved rollout, preserve the live SQLite state and resolve its
  persistence/restore path. The additive migration should run against a copy
  first. Rollback should restore a matching code/database backup: reverting only
  the code would reintroduce the old hashing behavior and can replay alerts.

The service automatically deploys `main`. Review and approval must precede any
merge. The proposed branch is separate; Render pull-request previews are off.
