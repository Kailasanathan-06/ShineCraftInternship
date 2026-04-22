def detect_changes(old_data, new_data):
    """Detect changes between old and new scan data."""
    changes = []
    for key, value in new_data.items():
        if key not in old_data or old_data[key] != value:
            changes.append({
                "field": key,
                "old": old_data[key],
                "new": value
            })
    return changes
