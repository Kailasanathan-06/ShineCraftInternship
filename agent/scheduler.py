"""
Scheduler for automatic asset scans
"""
import threading
import time
from datetime import datetime, timedelta
from django.core.cache import cache
from apps.assets.models import Asset, ScanResult
from apps.assets.scanner_adapter import execute_scan


class AutoScanScheduler:
    """Handle automatic scheduled scans"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.next_scan_time = None
    
    def get_next_scan_time(self, interval, scan_time):
        """Calculate next scan time based on interval and time"""
        now = datetime.now()
        hour, minute = map(int, scan_time.split(':'))
        
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if interval == 'hourly':
            if target_time <= now:
                target_time += timedelta(hours=1)
        elif interval == 'daily':
            if target_time <= now:
                target_time += timedelta(days=1)
        elif interval == 'weekly':
            if target_time <= now:
                target_time += timedelta(weeks=1)
        
        return target_time
    
    def execute_scan(self):
        """Execute a scan cycle"""
        try:
            print(f"[{datetime.now()}] Starting automatic scan...")
            data = execute_scan()
            
            comp = data["Asset Details"]["ComputerDetails"]["Computer system"]
            
            asset, created = Asset.objects.update_or_create(
                hostname=comp["Name"],
                defaults={
                    "service_tag": comp.get("service tag"),
                    "manufacturer": comp.get("manufacturer", ""),
                    "model": comp.get("model", ""),
                    "assigned_user": comp.get("logged_in_user", ""),
                }
            )
            
            ScanResult.objects.create(asset=asset, raw_output=data)
            
            print(f"[{datetime.now()}] Automatic scan completed for {asset.hostname}")
            
            # Update last scan time in cache
            cache.set('last_auto_scan', {
                'hostname': asset.hostname,
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            })
            
        except Exception as e:
            print(f"[{datetime.now()}] Automatic scan failed: {str(e)}")
            cache.set('last_auto_scan', {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'failed'
            })
    
    def run(self):
        """Main scheduler loop"""
        while self.running:
            config = cache.get('auto_scan_config')
            
            if not config or not config.get('enabled'):
                time.sleep(60)  # Check every minute
                continue
            
            now = datetime.now()
            interval = config.get('interval', 'daily')
            scan_time = config.get('time', '02:00')
            
            # Calculate next scan time
            if self.next_scan_time is None or now >= self.next_scan_time:
                self.next_scan_time = self.get_next_scan_time(interval, scan_time)
            
            # Check if it's time to scan (within 1-minute window)
            if now >= self.next_scan_time and now < (self.next_scan_time + timedelta(minutes=1)):
                self.execute_scan()
                self.next_scan_time = self.get_next_scan_time(interval, scan_time)
            
            time.sleep(30)  # Check every 30 seconds
    
    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            print("[Scheduler] Auto-scan scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[Scheduler] Auto-scan scheduler stopped")


# Global scheduler instance
_scheduler = None


def get_scheduler():
    """Get or create the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AutoScanScheduler()
    return _scheduler


def start_scheduler():
    """Start the auto-scan scheduler"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the auto-scan scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()
