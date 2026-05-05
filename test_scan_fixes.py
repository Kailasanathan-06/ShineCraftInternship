#!/usr/bin/env python
"""
Test script to validate scan functionality:
1. Manual scan (via API)
2. Automatic scan scheduling
3. Data extraction from scan results
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.cache import cache
from django.utils import timezone
from apps.assets.models import Asset, ScanResult
from agent.scheduler import AutoScanScheduler
from agent.scan_engine import run_full_scan, get_computer_return_data

def test_data_extraction():
    """Test that scan data structure is correct"""
    print("\n" + "="*60)
    print("TEST 1: Data Structure Validation")
    print("="*60)
    
    try:
        print("Running full scan to get data structure...")
        data = get_computer_return_data()
        
        print(f"✓ Scan completed at: {data.get('scan_timestamp')}")
        
        # Check root level Computer system
        comp_root = data.get("Computer system", {})
        if comp_root and comp_root.get("Name"):
            print(f"✓ Found 'Computer system' at root level with hostname: {comp_root['Name']}")
        else:
            print("✗ 'Computer system' not found at root level")
        
        # Check nested structure
        comp_nested = data.get("Asset Details", {}).get("ComputerDetails", {}).get("Computer system", {})
        if comp_nested and comp_nested.get("Name"):
            print(f"✓ Found 'Computer system' in nested structure: {comp_nested['Name']}")
        else:
            print("✗ 'Computer system' not found in nested structure")
        
        # Show available keys
        print(f"\n✓ Top-level keys in scan data: {list(data.keys())[:5]}...")
        return True, data
        
    except Exception as e:
        print(f"✗ Data extraction failed: {str(e)}")
        return False, None

def test_scheduler_timing():
    """Test scheduler timing calculations"""
    print("\n" + "="*60)
    print("TEST 2: Scheduler Timing Calculations")
    print("="*60)
    
    scheduler = AutoScanScheduler()
    now = datetime.now()
    
    test_cases = [
        ("hourly", "14:30"),    # Hourly at 30 minutes past
        ("daily", "02:00"),     # Daily at 2 AM
        ("weekly", "22:45"),    # Weekly at 10:45 PM
    ]
    
    for interval, scan_time in test_cases:
        try:
            next_scan = scheduler.get_next_scan_time(interval, scan_time)
            time_until = (next_scan - now).total_seconds() / 60
            print(f"✓ {interval.upper():8} at {scan_time}: Next scan in {time_until:6.1f} minutes")
        except Exception as e:
            print(f"✗ {interval.upper()} timing failed: {str(e)}")

def test_cache_config():
    """Test cache configuration storage"""
    print("\n" + "="*60)
    print("TEST 3: Scheduler Configuration Cache")
    print("="*60)
    
    try:
        # Set a test config
        config = {
            'enabled': True,
            'interval': 'daily',
            'time': '03:00'
        }
        cache.set('auto_scan_config', config, None)
        print(f"✓ Set cache config: {config}")
        
        # Retrieve it
        retrieved = cache.get('auto_scan_config')
        if retrieved == config:
            print(f"✓ Retrieved config matches: {retrieved}")
            return True
        else:
            print(f"✗ Retrieved config doesn't match")
            print(f"  Expected: {config}")
            print(f"  Got: {retrieved}")
            return False
            
    except Exception as e:
        print(f"✗ Cache test failed: {str(e)}")
        return False

def test_asset_storage():
    """Test Asset model storage"""
    print("\n" + "="*60)
    print("TEST 4: Asset Model Storage")
    print("="*60)
    
    try:
        # Create test asset
        test_hostname = f"TEST_HOST_{int(datetime.now().timestamp())}"
        asset, created = Asset.objects.get_or_create(
            hostname=test_hostname,
            defaults={
                'service_tag': 'SVC123',
                'manufacturer': 'Dell',
                'model': 'OptiPlex 7090',
                'assigned_user': 'test.user',
            }
        )
        
        status = "created" if created else "retrieved"
        print(f"✓ Asset {status}: {asset.hostname}")
        print(f"  - Service Tag: {asset.service_tag}")
        print(f"  - Manufacturer: {asset.manufacturer}")
        print(f"  - Model: {asset.model}")
        print(f"  - Assigned User: {asset.assigned_user}")
        
        # Try to retrieve it
        asset2 = Asset.objects.get(hostname=test_hostname)
        print(f"✓ Successfully retrieved asset: {asset2.hostname}")
        
        # Clean up
        asset.delete()
        print(f"✓ Cleaned up test asset")
        return True
        
    except Exception as e:
        print(f"✗ Asset storage test failed: {str(e)}")
        return False

def test_scan_result_storage(scan_data):
    """Test ScanResult model storage"""
    print("\n" + "="*60)
    print("TEST 5: ScanResult Model Storage")
    print("="*60)
    
    if not scan_data:
        print("✗ No scan data available (skipping)")
        return False
    
    try:
        # Get or create a test asset
        comp = scan_data.get("Computer system", {})
        hostname = comp.get("Name", "TestHost")
        
        asset, _ = Asset.objects.get_or_create(hostname=hostname)
        
        # Create scan result
        scan_result = ScanResult.objects.create(
            asset=asset,
            raw_output=scan_data,
            scan_status='Completed'
        )
        
        print(f"✓ Created ScanResult for {asset.hostname}")
        print(f"  - ID: {scan_result.id}")
        print(f"  - Status: {scan_result.scan_status}")
        print(f"  - Created At: {scan_result.created_at}")
        
        # Verify retrieval
        retrieved = ScanResult.objects.get(id=scan_result.id)
        print(f"✓ Retrieved ScanResult successfully")
        print(f"  - Asset: {retrieved.asset.hostname}")
        
        # Clean up
        scan_result.delete()
        print(f"✓ Cleaned up test ScanResult")
        return True
        
    except Exception as e:
        print(f"✗ ScanResult storage test failed: {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("SCAN FUNCTIONALITY TEST SUITE")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Test 1: Data extraction
    success, scan_data = test_data_extraction()
    results['Data Extraction'] = success
    
    # Test 2: Scheduler timing
    try:
        test_scheduler_timing()
        results['Scheduler Timing'] = True
    except Exception as e:
        print(f"✗ Scheduler timing failed: {str(e)}")
        results['Scheduler Timing'] = False
    
    # Test 3: Cache config
    results['Cache Config'] = test_cache_config()
    
    # Test 4: Asset storage
    results['Asset Storage'] = test_asset_storage()
    
    # Test 5: ScanResult storage
    results['ScanResult Storage'] = test_scan_result_storage(scan_data)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Scan functionality is working.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Review the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
