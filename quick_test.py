#!/usr/bin/env python
"""
Quick test utilities for scanning functionality
Run individual tests without full test suite
"""

import os
import sys
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.cache import cache
from apps.assets.models import Asset, ScanResult

def test_manual_scan():
    """Test manual scan functionality"""
    print("\n" + "="*60)
    print("MANUAL SCAN TEST")
    print("="*60)
    print("1. This sets scan_requested=True for all assets")
    print("2. Agents will pick up the request on next check-in")
    print("3. Agent runs scan and uploads data")
    print("")
    
    count = Asset.objects.update(scan_requested=True)
    print(f"✓ Set scan_requested=True for {count} asset(s)")
    print("\nWait for agents to check in and complete scans...")
    print("Monitor Asset model for updated scan data")

def test_schedule_scan(interval='daily', time='03:00'):
    """Test automatic scan scheduling"""
    print("\n" + "="*60)
    print("AUTOMATIC SCAN TEST")
    print("="*60)
    print(f"Scheduling {interval} scans at {time}")
    
    config = {
        'enabled': True,
        'interval': interval,
        'time': time
    }
    
    cache.set('auto_scan_config', config, None)
    print(f"✓ Config saved to cache: {json.dumps(config, indent=2)}")
    print("\nScheduler will:")
    print(f"  - Calculate next scan time based on {interval} interval")
    print(f"  - Use time {time} for the scan")
    print(f"  - Automatically trigger scan when time arrives")
    print(f"  - Calculate next scan time after completion")

def list_assets():
    """List all scanned assets"""
    print("\n" + "="*60)
    print("SCANNED ASSETS")
    print("="*60)
    
    assets = Asset.objects.all().order_by('-last_scan')
    if not assets:
        print("No assets found")
        return
    
    print(f"\nTotal assets: {assets.count()}\n")
    for asset in assets:
        scans = ScanResult.objects.filter(asset=asset).count()
        online = "ONLINE" if asset.is_online else "OFFLINE"
        print(f"  Host: {asset.hostname:30} | User: {asset.assigned_user:15} | Scans: {scans:3} | {online}")
        print(f"        Model: {asset.model or 'N/A':40} | Last: {asset.last_scan.strftime('%Y-%m-%d %H:%M:%S') if asset.last_scan else 'Never'}")

def show_last_scan():
    """Show details of last scan"""
    print("\n" + "="*60)
    print("LAST SCAN DETAILS")
    print("="*60)
    
    try:
        scan = ScanResult.objects.latest('created_at')
        asset = scan.asset
        
        print(f"\nAsset: {asset.hostname}")
        print(f"  Service Tag: {asset.service_tag}")
        print(f"  Manufacturer: {asset.manufacturer}")
        print(f"  Model: {asset.model}")
        print(f"  Assigned User: {asset.assigned_user}")
        print(f"\nScan Results:")
        print(f"  ID: {scan.id}")
        print(f"  Status: {scan.scan_status}")
        print(f"  Created: {scan.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show sample data
        data = scan.raw_output
        if data:
            print(f"\nScan Data Keys (first 10):")
            for key in list(data.keys())[:10]:
                print(f"    - {key}")
            
            comp = data.get("Computer system", {})
            if comp:
                print(f"\nComputer Details:")
                print(f"    - Name: {comp.get('Name')}")
                print(f"    - Manufacturer: {comp.get('manufacturer')}")
                print(f"    - Model: {comp.get('model')}")
                print(f"    - Service Tag: {comp.get('service tag')}")
    
    except ScanResult.DoesNotExist:
        print("No scan results found")

def check_scheduler_config():
    """Check current scheduler configuration"""
    print("\n" + "="*60)
    print("SCHEDULER CONFIGURATION")
    print("="*60)
    
    config = cache.get('auto_scan_config')
    if config:
        print("\n✓ Scheduler is configured:")
        print(f"    Enabled: {config.get('enabled')}")
        print(f"    Interval: {config.get('interval')}")
        print(f"    Time: {config.get('time')}")
    else:
        print("\n✗ No scheduler configuration found")
        print("  Use test_schedule_scan() to set up automatic scans")

def main():
    if len(sys.argv) < 2:
        print("\nUsage: python quick_test.py [command]")
        print("\nAvailable commands:")
        print("  manual              - Trigger manual scan on all assets")
        print("  daily [time]        - Schedule daily scans (default: 03:00)")
        print("  hourly [time]       - Schedule hourly scans (default: 02:00)")
        print("  weekly [time]       - Schedule weekly scans (default: 22:00)")
        print("  list                - List all assets")
        print("  lastscan            - Show last scan details")
        print("  config              - Show scheduler configuration")
        print("\nExamples:")
        print("  python quick_test.py manual")
        print("  python quick_test.py daily 02:00")
        print("  python quick_test.py hourly")
        print("  python quick_test.py list")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == 'manual':
        test_manual_scan()
    
    elif command == 'daily':
        time = sys.argv[2] if len(sys.argv) > 2 else '03:00'
        test_schedule_scan('daily', time)
    
    elif command == 'hourly':
        time = sys.argv[2] if len(sys.argv) > 2 else '02:00'
        test_schedule_scan('hourly', time)
    
    elif command == 'weekly':
        time = sys.argv[2] if len(sys.argv) > 2 else '22:00'
        test_schedule_scan('weekly', time)
    
    elif command == 'list':
        list_assets()
    
    elif command == 'lastscan':
        show_last_scan()
    
    elif command == 'config':
        check_scheduler_config()
    
    else:
        print(f"Unknown command: {command}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
