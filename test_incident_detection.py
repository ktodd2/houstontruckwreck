#!/usr/bin/env python3
"""
Test script to verify incident detection for the specific IH-69 Eastex incident
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import TranStarScraper
from models import Database, Settings

def test_specific_incident():
    """Test the specific incident that was missed"""
    
    # The exact incident from TranStar
    test_incident = "IH-69 Eastex Northbound After FM-1960	Heavy Truck, Stall	Right Shoulder	Verified at 3:16 PM"
    
    print("Testing incident detection for:")
    print(f"'{test_incident}'")
    print("-" * 80)
    
    # Initialize scraper
    scraper = TranStarScraper()
    
    # Test if this incident would be detected as relevant
    is_relevant = scraper.is_relevant_incident(test_incident)
    print(f"Is relevant incident: {is_relevant}")
    
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
        
        # Test individual components
        text_lower = test_incident.lower()
        has_heavy_truck = 'heavy truck' in text_lower
        has_stall = 'stall' in text_lower
        is_highway = 'ih-69' in text_lower or 'eastex' in text_lower
        
        print(f"Has 'heavy truck': {has_heavy_truck}")
        print(f"Has 'stall': {has_stall}")
        print(f"Is highway location: {is_highway}")
        
    else:
        print("✅ SUCCESS: This incident would be detected!")
        
        # Test incident creation
        try:
            cell_texts = test_incident.split('\t')
            incident = scraper.create_incident_from_text(cell_texts, test_incident)
            
            if incident:
                print("\n📋 Created incident:")
                print(f"Location: {incident.location}")
                print(f"Description: {incident.description}")
                print(f"Time: {incident.incident_time}")
                print(f"Severity: {incident.severity}")
                print(f"Hash: {incident.incident_hash}")
            else:
                print("❌ Failed to create incident object")
                
        except Exception as e:
            print(f"❌ Error creating incident: {e}")

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

def check_current_settings():
    """Check current app settings"""
    print("\n" + "="*80)
    print("CURRENT SETTINGS")
    print("="*80)
    
    db = Database()
    include_stalls = Settings.get_include_stalls(db)
    
    print(f"Include stalls: {include_stalls}")
    
    if not include_stalls:
        print("⚠️  WARNING: Stalls are currently DISABLED!")
        print("   This means heavy truck stalls will NOT trigger alerts.")
        print("   To enable: Go to admin settings and enable 'Include Stalls'")

if __name__ == "__main__":
    print("HOUSTON TRUCK WRECK - INCIDENT DETECTION TEST")
    print("=" * 80)
    
    # Check current settings first
    check_current_settings()
    
    # Test the specific incident
    test_specific_incident()
    
    # Test pattern matching
    test_pattern_matching()
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
