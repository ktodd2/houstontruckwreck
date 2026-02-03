# Testing Patterns

**Analysis Date:** 2026-02-03

## Test Framework

**Runner:**
- Python's built-in `unittest` module (implicit, not explicit imports)
- Tests can be run directly with `python test_*.py`

**Assertion Library:**
- Python standard `assert` statements
- No external assertion library detected (no pytest, unittest assertions explicitly used)

**Run Commands:**
```bash
python test_system.py              # Run system integration tests
python test_incident_detection.py  # Run incident detection tests
python test_improvements.py        # Run improvement/formatting tests
```

## Test File Organization

**Location:**
- Tests are co-located with source code at project root
- Test files: `test_system.py`, `test_incident_detection.py`, `test_improvements.py`
- Source files: `app.py`, `models.py`, `scraper.py`, `email_service.py`

**Naming:**
- Prefix `test_` for test files: `test_system.py`, `test_incident_detection.py`
- Functions use prefix `test_`: `test_imports()`, `test_database()`, `test_scraper()`
- Descriptive names: `test_specific_incident()`, `test_pattern_matching()`

**Structure:**
```
[project-root]/
├── test_system.py                  # System-wide integration tests
├── test_incident_detection.py      # Incident detection logic tests
├── test_improvements.py            # Email/formatting feature tests
└── [source files]
```

## Test Structure

**Suite Organization from `test_system.py`:**
```python
def test_imports():
    """Test that all required modules can be imported"""
    # ... test code

def test_database():
    """Test database creation and basic operations"""
    # ... test code

def test_scraper():
    """Test web scraper functionality"""
    # ... test code

def test_email_service():
    """Test email service (without actually sending)"""
    # ... test code

def test_flask_app():
    """Test Flask app creation"""
    # ... test code

def main():
    """Run all tests"""
    tests = [
        test_imports,
        test_database,
        test_scraper,
        test_email_service,
        test_flask_app
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"📊 Test Results: {passed}/{total} tests passed")
```

**Patterns:**
- Setup: Create fresh test instances before each test
- Teardown: Clean up test databases with `os.remove("test_database.db")`
- Assertion: Return boolean `True`/`False` from test functions
- Reporting: Print status with emoji indicators (`✅`, `❌`)

## Test Types

**Unit Tests (from `test_system.py`):**
- `test_imports()`: Verifies all required packages can be imported
- `test_database()`: Tests database creation and `Subscriber.add()` operation
- `test_scraper()`: Tests incident classification logic with test cases
- `test_email_service()`: Tests email content generation without sending

**Scope:** Individual components (database, scraper, email service)

**Example from `test_system.py` lines 55-91:**
```python
def test_scraper():
    """Test web scraper functionality"""
    print("\n🕷️  Testing scraper...")

    try:
        from scraper import TranStarScraper

        scraper = TranStarScraper()

        # Test incident classification
        test_cases = [
            ("Semi-truck accident on I-45", True),
            ("18-wheeler stalled on highway", True),
            ("Hazmat spill reported", True),
            ("Car accident on surface street", False),
            ("Traffic light out", False)
        ]

        all_passed = True
        for text, expected in test_cases:
            result = scraper.is_relevant_incident(text)
            if result == expected:
                print(f"✅ '{text}' -> {result}")
            else:
                print(f"❌ '{text}' -> {result} (expected {expected})")
                all_passed = False

        if all_passed:
            print("✅ Scraper classification working correctly")
            return True
        else:
            print("❌ Scraper classification has issues")
            return False

    except Exception as e:
        print(f"❌ Scraper error: {e}")
        return False
```

**Integration Tests (from `test_incident_detection.py`):**
- `test_specific_incident()`: Tests real incident detection from TranStar format
- `test_pattern_matching()`: Tests 9 different incident patterns
- `check_current_settings()`: Verifies app settings affect incident detection

**Scope:** Multiple components working together (scraper settings + incident detection)

**Example from `test_incident_detection.py` lines 78-103:**
```python
def test_pattern_matching():
    """Test various patterns that should match truck incidents"""

    test_cases = [
        "IH-69 Eastex Northbound After FM-1960 Heavy Truck, Stall Right Shoulder Verified at 3:16 PM",
        "Heavy Truck Stall on IH-45 North",
        "Semi-truck accident on I-10 West",
        "18-wheeler rollover on US-59",
        "Commercial vehicle breakdown on Beltway 8",
        "Tractor-trailer crash on Hardy Toll Road",
        "Big rig stalled on Loop 610",
        "Freight truck accident on Eastex Freeway",
        "Heavy truck spill on I-45 South",
        "Regular car accident on Main Street"  # Should NOT match
    ]

    scraper = TranStarScraper()

    print("\n" + "="*80)
    print("PATTERN MATCHING TESTS")
    print("="*80)

    for i, test_case in enumerate(test_cases, 1):
        is_relevant = scraper.is_relevant_incident(test_case)
        status = "✅ MATCH" if is_relevant else "❌ NO MATCH"
        print(f"{i:2d}. {status} | {test_case}")
```

**System Tests (from `test_system.py` main()):**
- Runs all unit tests in sequence
- Generates summary report
- Provides next steps if tests pass

## Test Data

**Test fixtures in `test_system.py`:**
```python
# Incident classification test cases (line 65-71)
test_cases = [
    ("Semi-truck accident on I-45", True),
    ("18-wheeler stalled on highway", True),
    ("Hazmat spill reported", True),
    ("Car accident on surface street", False),
    ("Traffic light out", False)
]
```

**Test incidents in `test_improvements.py`:**
```python
# Location extraction test cases (line 21-39)
test_cases = [
    # Test @ symbol preservation
    "Hardy Toll Road NB @ Richey Rd heavy truck accident",
    "I-45 @ Beltway 8 semi-truck collision",

    # Test conversion to @ format
    "US-290 at Northwest Freeway truck accident",
    "I-10 near Downtown heavy truck stall",
    # ... more cases
]
```

**Location:**
- Inline test data in each test function
- No separate fixtures or factory files
- Real-world incident text examples from Houston TranStar

## Mocking

**Framework:**
- No external mocking library used (no `unittest.mock`, `pytest-mock`, `responses`)
- Manual test data substitution instead of true mocks

**Patterns:**

**Creating test objects directly:**
```python
# From test_system.py lines 104-109
test_incident = Incident(
    location="I-45 at Beltway 8",
    description="Semi-truck accident blocking lanes",
    incident_time="14:30",
    severity=3
)
```

**Creating test database instances:**
```python
# From test_system.py line 37
db = Database("test_database.db")  # Creates separate test DB file
```

**Avoiding actual email sending:**
```python
# From test_system.py lines 112-119
subject, html_content = email_service.create_html_email([(test_incident, 1)])

if subject and html_content and "Semi-truck accident" in html_content:
    print("✅ Email content generation working")
    return True
else:
    print("❌ Email content generation failed")
    return False
```

**What to Mock:**
- Skip SMTP operations (test only email content generation)
- Use test database file instead of production database
- Don't make actual HTTP requests to TranStar

**What NOT to Mock:**
- Incident classification logic (test the actual implementation)
- Database schema creation (test init_db works)
- Flask routing and login (test the actual flow)

## Database Testing

**Test database pattern:**
```python
# From test_system.py lines 36-45
from models import Database, Subscriber, AdminUser

# Create test database
db = Database("test_database.db")

# Test adding a subscriber
success = Subscriber.add(db, "test@example.com")
if success:
    print("✅ Database operations working")

    # Clean up
    os.remove("test_database.db")
    return True
```

**Patterns:**
- Create separate test database file for each test
- Use Database class constructor with custom path: `Database("test_database.db")`
- Delete test database file after test completes: `os.remove("test_database.db")`
- Test both success and failure cases (`sqlite3.IntegrityError` handling)

## Flask Testing

**Test pattern from `test_system.py` lines 125-144:**
```python
def test_flask_app():
    """Test Flask app creation"""
    print("\n🌐 Testing Flask app...")

    try:
        from app import app

        with app.test_client() as client:
            # Test login page
            response = client.get('/login')
            if response.status_code == 200:
                print("✅ Flask app routes working")
                return True
            else:
                print(f"❌ Flask app error: status {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ Flask app error: {e}")
        return False
```

**Patterns:**
- Use `app.test_client()` context manager
- Test route accessibility with HTTP methods
- Check status code responses
- Don't test login-protected routes without authentication

## Error Testing

**Pattern from `test_incident_detection.py` lines 30-46:**
```python
if not is_relevant:
    print("❌ PROBLEM: This incident would NOT be detected!")

    # Check stalls setting
    db = Database()
    include_stalls = Settings.get_include_stalls(db)
    print(f"Include stalls setting: {include_stalls}")

    if not include_stalls:
        print("🔧 ISSUE: Stalls are disabled in settings!")
        print("Enabling stalls...")
        Settings.set_include_stalls(db, True)

        # Test again
        is_relevant_after = scraper.is_relevant_incident(test_incident)
        print(f"Is relevant after enabling stalls: {is_relevant_after}")
```

**Patterns:**
- Test error conditions by checking for False returns
- Print diagnostic info when errors occur
- Test both before/after state changes
- Provide remediation suggestions in output

## Coverage

**Requirements:**
- Not enforced; no coverage tool configured

**View Coverage:**
- Not applicable (no test coverage tool detected)

## Test Output Format

**Console output pattern with emojis:**
```
🔍 Testing imports...
✅ All required packages imported successfully

🗄️  Testing database...
✅ Database operations working

🕷️  Testing scraper...
✅ 'Semi-truck accident on I-45' -> True
✅ 'Hazmat spill reported' -> True
❌ 'Car accident on surface street' -> False (expected False)
✅ Scraper classification working correctly

📧 Testing email service...
✅ Email content generation working

🌐 Testing Flask app...
✅ Flask app routes working

==================================================
📊 Test Results: 5/5 tests passed
🎉 All tests passed! System is ready to run.
```

## Running Tests

**From command line:**
```bash
python test_system.py              # Full system test
python test_incident_detection.py  # Incident detection test
python test_improvements.py        # Feature-specific test
```

**Test execution:**
- No test runner framework (unittest/pytest discovery not used)
- Tests must be run individually
- Each test file calls `main()` or test functions directly
- Exit code indicates pass/fail: `sys.exit(0)` for success, `sys.exit(1)` for failure

## Assertion Style

**Pattern from tests:**
```python
# Return boolean from test function
if all_passed:
    print("✅ Scraper classification working correctly")
    return True
else:
    print("❌ Scraper classification has issues")
    return False
```

**Collections:**
```python
# Check if list has expected size
if len(new_incidents) > 0:
    # process
```

**String content:**
```python
# Check if expected text exists in response
if subject and html_content and "Semi-truck accident" in html_content:
    return True
```

**Exception catching:**
```python
try:
    # test operation
except Exception as e:
    print(f"❌ Error: {e}")
    return False
```

---

*Testing analysis: 2026-02-03*
