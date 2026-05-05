# Scan Functionality Fixes - Summary Report

## Issues Identified and Fixed

### Issue 1: Manual Scan Not Storing Data in Asset Model ✓ FIXED
**Problem:** When manual scan was triggered via the dashboard, data was not being stored in the Asset model.

**Root Cause:** The data structure returned by `get_computer_return_data()` has the computer details at both:
- Root level: `data["Computer system"]`
- Nested level: `data["Asset Details"]["ComputerDetails"]["Computer system"]`

The `agent_upload()` view only checked the nested structure and failed when it wasn't there.

**Solution:** Updated `agent_upload()` in `apps/assets/views.py` to:
1. First try to extract hostname from root-level `"Computer system"`
2. Fall back to nested structure if not found
3. Properly extract all asset fields (service_tag, manufacturer, model, assigned_user)
4. Store full scan result in ScanResult model

**Files Modified:** `apps/assets/views.py` (line 125-160)

---

### Issue 2: Automatic Scheduler Not Working for Hourly/Daily/Weekly ✓ FIXED
**Problem:** The scheduler's `get_next_scan_time()` function had incorrect logic for calculating scan times.

**Root Cause:** 
- For hourly scans: was trying to set both hour and minute, but should only set minute
- For daily scans: worked but needed error handling
- For weekly scans: worked but needed error handling

**Solution:** Rewrote `get_next_scan_time()` in `agent/scheduler.py`:

```python
# HOURLY: Scan at MM:SS of every hour (e.g., 14:30 = every hour at 30 minutes)
# DAILY: Scan at HH:MM every day (e.g., 02:00 = 2 AM daily)
# WEEKLY: Scan at HH:MM once per week (e.g., 22:45 = 10:45 PM weekly)
```

Added proper error handling for invalid time formats.

**Files Modified:** `agent/scheduler.py` (line 21-48)

---

### Issue 3: Scheduler Data Extraction Path Error ✓ FIXED
**Problem:** The scheduler's `execute_scan()` was trying to access scan data with wrong path:
```python
comp = data["Asset Details"]["ComputerDetails"]["Computer system"]  # ✗ WRONG
```

**Root Cause:** This nested path doesn't always exist. The scan data structure has "Computer system" at root level.

**Solution:** Updated `execute_scan()` in `agent/scheduler.py` to:
1. Try root-level extraction first: `data.get("Computer system", {})`
2. Fall back to nested structure if needed
3. Validate hostname exists before proceeding
4. Properly handle missing keys with `.get()` instead of direct access

**Files Modified:** `agent/scheduler.py` (line 43-67)

---

## How the Scan Flow Works

### Manual Scan Flow
```
Dashboard "Manual Scan" Button
    ↓
POST to /assets/scan/
    ↓
ManualScanAPIView sets scan_requested=True on all assets
    ↓
Client agent checks in and gets action="scan"
    ↓
Agent calls run_full_scan()
    ↓
Agent uploads data to /assets/agent/upload/
    ↓
agent_upload() stores data in Asset and ScanResult models ✓
```

### Automatic Scan Flow (Hourly/Daily/Weekly)
```
Dashboard "Automatic Scan" Button
    ↓
POST to /dashboard/api/schedule-scan/
    ↓
Config stored in cache: {enabled, interval, time}
    ↓
DashboardConfig.ready() starts AutoScanScheduler
    ↓
Scheduler calculates next_scan_time based on interval
    ↓
When server time reaches next_scan_time:
    - Scheduler calls execute_scan()
    - Gets scan data
    - Stores in Asset and ScanResult models ✓
    - Calculates new next_scan_time for next occurrence
```

---

## Time Format Understanding

When scheduling automatic scans, the time format is **HH:MM** (24-hour):

| Interval | Time Format | Example | Meaning |
|----------|------------|---------|---------|
| **Hourly** | MM (minutes) | 02:30 | Every hour at 30 minutes past (14:30, 15:30, 16:30...) |
| **Daily** | HH:MM | 02:00 | Every day at 2:00 AM |
| **Weekly** | HH:MM | 22:45 | Once per week at 10:45 PM |

---

## Testing the Fixes

Run the comprehensive test script:
```bash
python test_scan_fixes.py
```

This tests:
1. ✓ Data extraction from scan results
2. ✓ Scheduler timing calculations
3. ✓ Cache configuration storage
4. ✓ Asset model storage
5. ✓ ScanResult model storage

All tests should pass: **5/5 ✓**

---

## Verification Checklist

- [x] Manual scan stores data in Asset model
- [x] Manual scan stores raw JSON in ScanResult model
- [x] Automatic scan scheduler calculates correct intervals
- [x] Hourly scans use minute value from time field
- [x] Daily scans use HH:MM from time field
- [x] Weekly scans use HH:MM from time field
- [x] Scheduler handles invalid time formats gracefully
- [x] Both root-level and nested data structures supported
- [x] All required asset fields extracted (hostname, service_tag, manufacturer, model, assigned_user)
- [x] Change detection triggers on new scan data

---

## Configuration Example

To schedule scans via the dashboard API:

### Daily at 3:00 AM
```json
POST /dashboard/api/schedule-scan/
{
  "interval": "daily",
  "time": "03:00",
  "notifications": true
}
```

### Hourly at 45 minutes past
```json
POST /dashboard/api/schedule-scan/
{
  "interval": "hourly",
  "time": "02:45",
  "notifications": true
}
```

### Weekly at 10:30 PM
```json
POST /dashboard/api/schedule-scan/
{
  "interval": "weekly",
  "time": "22:30",
  "notifications": true
}
```

---

## Notes for Future Development

1. **Client Agent Requirement**: Manual and automatic scans require the Python client agent to be running on each scanned system
2. **Scheduler Thread**: The AutoScanScheduler runs as a daemon thread in the Django app process
3. **Cache Storage**: Schedule configuration is stored in Django's cache system (not persistent across app restarts without cache backend configuration)
4. **Data Persistence**: All scan results are persisted in the database (ScanResult model)
5. **Change Detection**: Previous scan comparison happens automatically when new data arrives

