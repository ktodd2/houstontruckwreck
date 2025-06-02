#!/usr/bin/env python3
"""
Test script for Houston Traffic Monitor
Run this to verify all components are working correctly
"""

import sys
import os
from datetime import datetime

def test_imports():
    """Test that all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        import requests
        import bs4
        import flask
        import sqlite3
        from werkzeug.security import generate_password_hash
        from apscheduler.schedulers.background import BackgroundScheduler
        print("✅ All required packages imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def test_database():
    """Test database creation and basic operations"""
    print("\n🗄️  Testing database...")
    
    try:
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
        else:
            print("❌ Database operations failed")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

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

def test_email_service():
    """Test email service (without actually sending)"""
    print("\n📧 Testing email service...")
    
    try:
        from email_service import EmailService
        from models import Incident
        
        email_service = EmailService()
        
        # Create test incident
        test_incident = Incident(
            location="I-45 at Beltway 8",
            description="Semi-truck accident blocking lanes",
            incident_time="14:30",
            severity=3
        )
        
        # Test email content creation
        subject, html_content = email_service.create_html_email([(test_incident, 1)])
        
        if subject and html_content and "Semi-truck accident" in html_content:
            print("✅ Email content generation working")
            return True
        else:
            print("❌ Email content generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Email service error: {e}")
        return False

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

def main():
    """Run all tests"""
    print("🚛 Houston Traffic Monitor - System Test")
    print("=" * 50)
    
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
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready to run.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure your email settings")
        print("2. Run: python app.py")
        print("3. Open http://localhost:5000 in your browser")
        print("4. Login with admin/admin123 (change this password!)")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
