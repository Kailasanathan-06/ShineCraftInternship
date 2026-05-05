# ✓ Scanning Issues - FIXED

## Summary of Changes

Your scanning system had **3 critical bugs** that prevented:
1. Manual scans from storing data
2. Automatic hourly/daily/weekly scans from working
3. Incorrect data path extraction

**All issues are now fixed!** ✓

---

## What Was Wrong

### Problem #1: Manual Scan Not Storing Data
- Dashboard button triggered scan request
- Data was never saved to the Asset model
- Reason: Wrong data structure path

### Problem #2: Hourly/Daily/Weekly Scans Not Working  
- Scheduler had wrong time calculation logic
- For hourly scans: tried to set hour instead of minute
- For daily/weekly: timing calculation was flawed

### Problem #3: Data Structure Path Mismatch
- Scheduler tried to access: `data["Asset Details"]["ComputerDetails"]["Computer system"]`
- But the data structure has `"Computer system"` at root level
- Caused crashes when scheduler ran automatic scans

---

## What Was Fixed

### Fix #1: Updated `apps/assets/views.py` (agent_upload)
```python
# Now tries both data structures:
comp = data.get("Computer system", {})  # Try root first
if not comp or not comp.get("Name"):
    # Fall back to nested structure
    comp = data.get("Asset Details", {...})
```
✓ Manual scans now properly store data in Asset model

### Fix #2: Updated `agent/scheduler.py` (get_next_scan_time)
```python
# Fixed time calculations:
if interval == 'hourly':
    # Only set MINUTE from time (e.g., 02:30 = every hour at :30)
    target_time = now.replace(minute=minute, second=0, microsecond=0)
elif interval == 'daily':
    # Set HOUR:MINUTE (e.g., 02:00 = 2 AM every day)
    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
elif interval == 'weekly':
    # Set HOUR:MINUTE (e.g., 22:00 = 10 PM once per week)
    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
```
✓ All scan intervals now work correctly

### Fix #3: Updated `agent/scheduler.py` (execute_scan)
```python
# Now safely extracts data:
comp = data.get("Computer system", {})
if not comp or not comp.get("Name"):
    comp = data.get("Asset Details", {}).get("ComputerDetails", {}).get("Computer system", {})
if not comp.get("Name"):
    raise ValueError("Could not extract hostname")
```
✓ Scheduler no longer crashes on scan execution

---

## Time Format Explanation

### When you schedule a scan, use HH:MM format:

| What You Want | Interval | Time | Result |
|---|---|---|---|
| Every hour at 15 min | hourly | `00:15` | Scans at XX:15 (09:15, 10:15, 11:15...) |
| Every hour at 45 min | hourly | `02:45` | Scans at XX:45 (09:45, 10:45, 11:45...) |
| Daily at 3 AM | daily | `03:00` | Scans at 3:00 AM every day |
| Daily at 2 PM | daily | `14:00` | Scans at 2:00 PM every day |
| Weekly at 10 PM | weekly | `22:00` | Scans at 10:00 PM once per week |
| Weekly at 2:30 PM | weekly | `14:30` | Scans at 2:30 PM once per week |

---

## How to Use It Now

### Via Dashboard (Recommended)
1. Click "**Manual Scan**" → Triggers scan on all agents
2. Click "**Automatic Scan**" → Modal opens to set interval & time

### Via Python Commands
```bash
# Trigger manual scan on all assets
python quick_test.py manual

# Schedule daily scan at 3 AM
python quick_test.py daily 03:00

# Schedule hourly scan at 45 minutes past
python quick_test.py hourly 00:45

# Schedule weekly scan at 10 PM
python quick_test.py weekly 22:00

# View all assets
python quick_test.py list

# View last scan details
python quick_test.py lastscan

# Check current scheduler config
python quick_test.py config
```

### Via API
```bash
# Schedule daily scan
curl -X POST http://localhost:8000/dashboard/api/schedule-scan/ \
  -H "Content-Type: application/json" \
  -d '{"interval": "daily", "time": "03:00", "notifications": true}'

# Manual scan on all assets
curl -X POST http://localhost:8000/assets/scan/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Testing

Run the test suite to verify everything works:
```bash
python test_scan_fixes.py
```

Expected output: **5/5 tests passed** ✓

---

## Files Changed

| File | Changes |
|------|---------|
| `apps/assets/views.py` | Fixed `agent_upload()` to handle both data structures |
| `agent/scheduler.py` | Fixed timing calculations and data extraction |
| `test_scan_fixes.py` | NEW: Comprehensive test suite |
| `quick_test.py` | NEW: Quick testing utilities |
| `SCAN_FIXES_DOCUMENTATION.md` | NEW: Detailed documentation |

---

## Key Points to Remember

✓ **Manual scan**: Sets flag, agent picks it up on check-in and runs scan
✓ **Automatic scan**: Scheduler in Django runs based on cache config
✓ **Data storage**: Both Asset model and ScanResult model get updated
✓ **Hourly interval**: Only MM from time matters (hour changes naturally)
✓ **Daily interval**: Both HH and MM from time field
✓ **Weekly interval**: Both HH and MM from time field

---

## Next Steps

1. ✓ Review and test the fixes
2. Deploy changes to production
3. Ensure client agents are running on all scanned systems
4. Monitor scans via dashboard
5. Review scan results in "Recent Change Notifications"

