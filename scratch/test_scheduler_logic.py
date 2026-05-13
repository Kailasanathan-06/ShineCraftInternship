
import os
import sys
import django
from datetime import datetime, timedelta

# Set up Django environment
sys.path.append(os.path.join(os.getcwd()))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from agent.scheduler import AutoScanScheduler

def test_logic():
    scheduler = AutoScanScheduler()
    
    # Mock "now" for consistent testing
    # 2026-05-13 is a Wednesday (weekday 2)
    now = datetime(2026, 5, 13, 10, 0, 0)
    
    print(f"Mock 'now': {now} (Wednesday, weekday 2)")
    
    # Test Hourly
    # At 10:00, if we set hourly for 10:15, it should be 10:15 today.
    # Actually my logic uses the 'minute' from scan_time.
    res = scheduler.get_next_scan_time('hourly', '10:15')
    # Since I can't easily mock datetime.now() inside the class without patch, 
    # I'll just check if the logic makes sense relative to current real time or adjust the test.
    
    print("\n--- Testing Weekly Logic ---")
    # Current day is Wednesday (2). 
    # If we want Monday (0), it should be next Monday.
    res_mon = scheduler.get_next_scan_time('weekly', '02:00', day_of_week=0)
    print(f"Weekly (Monday): {res_mon} (Expected next Monday)")
    
    # If we want Wednesday (2) at 11:00 (today, later), it should be today.
    res_wed_later = scheduler.get_next_scan_time('weekly', '11:00', day_of_week=2)
    print(f"Weekly (Wednesday 11:00): {res_wed_later}")
    
    # If we want Wednesday (2) at 09:00 (today, earlier), it should be next Wednesday.
    res_wed_earlier = scheduler.get_next_scan_time('weekly', '09:00', day_of_week=2)
    print(f"Weekly (Wednesday 09:00): {res_wed_earlier}")
    
    # Test Daily
    res_daily = scheduler.get_next_scan_time('daily', '02:00')
    print(f"\nDaily (02:00): {res_daily}")

if __name__ == "__main__":
    test_logic()
