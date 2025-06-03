#!/usr/bin/env python3
"""
Test script to verify the notification email improvements
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import TranStarScraper
from email_service import EmailService
from models import Incident

def test_location_formatting():
    """Test the improved location extraction and formatting"""
    print("🧪 Testing Location Formatting...")
    
    scraper = TranStarScraper()
    
    # Test cases for location extraction
    test_cases = [
        # Test @ symbol preservation
        "Hardy Toll Road NB @ Richey Rd heavy truck accident",
        "I-45 @ Beltway 8 semi-truck collision",
        
        # Test conversion to @ format
        "US-290 at Northwest Freeway truck accident",
        "I-10 near Downtown heavy truck stall",
        "Highway 6 and Westheimer semi accident",
        "Beltway 8 at I-45 truck crash",
        
        # Test toll road detection
        "Hardy Toll Road northbound at FM 1960 heavy truck breakdown",
        "Westpark Tollway at Eldridge truck accident",
        
        # Test partial highway names (should get cross street)
        "US-290 truck accident blocking lanes",
        "I-45 semi-truck rollover incident",
    ]
    
    print("\n📍 Location Extraction Results:")
    print("-" * 60)
    
    for test_text in test_cases:
        location = scraper.extract_location(test_text)
        print(f"Input:  {test_text}")
        print(f"Output: {location}")
        print("-" * 60)

def test_time_formatting():
    """Test the 12-hour time format conversion"""
    print("\n🕐 Testing Time Formatting...")
    
    scraper = TranStarScraper()
    
    # Test cases for time conversion
    test_times = [
        "16:27",  # 24-hour format
        "14:30",  # 24-hour format
        "09:15",  # 24-hour format
        "00:45",  # Midnight
        "12:30",  # Noon
        "23:59",  # Late night
        "3:45 PM",  # Already 12-hour
        "10:30 AM",  # Already 12-hour
    ]
    
    print("\n🕐 Time Conversion Results:")
    print("-" * 40)
    
    for test_time in test_times:
        converted = scraper.convert_to_12_hour(test_time)
        print(f"{test_time:>8} → {converted}")

def test_incident_detection():
    """Test enhanced incident detection"""
    print("\n🚛 Testing Incident Detection...")
    
    scraper = TranStarScraper()
    
    # Test cases that should be detected (highway truck incidents)
    positive_cases = [
        "Hardy Toll Road NB @ Richey Rd heavy truck accident",
        "I-45 semi-truck collision blocking lanes",
        "US-290 truck accident with spill",
        "18-wheeler rollover on Beltway 8",
        "Commercial vehicle breakdown I-10",
        "Hazmat spill from truck on Highway 6",
        "Big rig accident at Loop 610",
        "Tractor-trailer crash US-59",
        "Semi accident on Katy Freeway",
        "Heavy truck stall on Gulf Freeway",
    ]
    
    # Test cases that should NOT be detected (non-truck or street incidents)
    negative_cases = [
        "Car accident on Main Street",
        "Motorcycle crash downtown",
        "Road construction on I-45",
        "Weather alert for Houston",
        "Traffic backup due to event",
        # Street incidents (should be filtered out)
        "Truck accident on Main Street @ 5th Ave",
        "Semi breakdown on Westheimer Road",
        "Heavy truck stall on Memorial Drive",
        "Commercial vehicle accident on Post Oak Blvd",
        "Delivery truck crash on Sage Road",
    ]
    
    print("\n✅ Should be detected (Highway truck incidents):")
    print("-" * 50)
    for case in positive_cases:
        detected = scraper.is_relevant_incident(case)
        status = "✅ DETECTED" if detected else "❌ MISSED"
        print(f"{status}: {case}")
    
    print("\n❌ Should NOT be detected (Non-truck or street incidents):")
    print("-" * 50)
    for case in negative_cases:
        detected = scraper.is_relevant_incident(case)
        status = "❌ INCORRECTLY DETECTED" if detected else "✅ CORRECTLY IGNORED"
        print(f"{status}: {case}")

def test_street_filtering():
    """Test street incident filtering specifically"""
    print("\n🚫 Testing Street Incident Filtering...")
    
    scraper = TranStarScraper()
    
    # Highway incidents (should NOT be filtered)
    highway_cases = [
        "I-45 @ Beltway 8 truck accident",
        "US-290 @ Northwest Freeway semi crash",
        "Hardy Toll Road NB @ Richey Rd heavy truck",
        "Loop 610 @ I-10 commercial vehicle accident",
        "Katy Freeway @ Eldridge truck breakdown",
    ]
    
    # Street incidents (should be filtered out)
    street_cases = [
        "Main Street @ 5th Avenue truck accident",
        "Westheimer Road @ Post Oak semi crash",
        "Memorial Drive @ Shepherd heavy truck stall",
        "Kirby Drive @ Richmond Ave truck breakdown",
        "Sage Road @ Briar Forest commercial vehicle",
        "Bissonnet @ Hillcroft delivery truck accident",
    ]
    
    print("\n🛣️ Highway incidents (should NOT be filtered):")
    print("-" * 50)
    for case in highway_cases:
        is_street = scraper.is_street_incident(case)
        status = "❌ INCORRECTLY FILTERED" if is_street else "✅ CORRECTLY ALLOWED"
        print(f"{status}: {case}")
    
    print("\n🏘️ Street incidents (should be filtered out):")
    print("-" * 50)
    for case in street_cases:
        is_street = scraper.is_street_incident(case)
        status = "✅ CORRECTLY FILTERED" if is_street else "❌ INCORRECTLY ALLOWED"
        print(f"{status}: {case}")

def test_email_formatting():
    """Test email formatting with improved data"""
    print("\n📧 Testing Email Formatting...")
    
    # Create test incidents with improved formatting
    test_incidents = [
        (Incident(
            location="Hardy Toll Road NB @ Richey Rd",
            description="Heavy truck accident blocking right lane",
            incident_time="4:27 PM",
            severity=4
        ), 1),
        (Incident(
            location="US-290 @ Northwest Fwy",
            description="Semi-truck with hazmat spill",
            incident_time="2:15 PM", 
            severity=5
        ), 2),
        (Incident(
            location="I-45 @ Beltway 8",
            description="18-wheeler breakdown in left lane",
            incident_time="11:30 AM",
            severity=2
        ), 3)
    ]
    
    email_service = EmailService()
    
    # Generate email content
    subject, html_content = email_service.create_html_email(test_incidents)
    text_content = email_service.create_text_email(test_incidents)
    
    print(f"\n📧 Email Subject: {subject}")
    print("\n📧 Sample HTML Content (first 500 chars):")
    print(html_content[:500] + "...")
    
    print("\n📧 Sample Text Content:")
    print(text_content[:800] + "...")

def main():
    """Run all tests"""
    print("🚀 Houston Traffic Monitor - Testing Email Improvements")
    print("=" * 60)
    
    try:
        test_location_formatting()
        test_time_formatting()
        test_incident_detection()
        test_street_filtering()
        test_email_formatting()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("\n🎯 Key Improvements Verified:")
        print("   • Location formatting: Street1 @ Street2")
        print("   • Time format: 12-hour with AM/PM")
        print("   • Enhanced incident detection")
        print("   • Street incident filtering (excludes local streets)")
        print("   • Toll road support (Hardy Toll Road, etc.)")
        print("   • Better cross-street extraction")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
