from ShineCraftInternship.apps.notifications.models import ChangeNotification

def detect_changes(asset, old_data, new_data):
    """
    Compares the old JSON scan data with the new JSON scan data
    and generates ChangeNotification records if differences exist.
    """
    if not old_data or not new_data:
        return
    
    # 1. Compare Memory
    try:
        old_mem = old_data.get("Asset Details", {}).get("ComputerDetails", {}).get("Hardware", {}).get("Memory", "Unknown")
        new_mem = new_data.get("Asset Details", {}).get("ComputerDetails", {}).get("Hardware", {}).get("Memory", "Unknown")
        
        if str(old_mem) != str(new_mem) and new_mem != "Unknown":
            ChangeNotification.objects.create(
                asset=asset,
                field_name="Memory",
                old_value=str(old_mem),
                new_value=str(new_mem)
            )
    except Exception as e:
        print(f"Diff error Memory: {e}")

    # 2. Compare Software Additions/Removals
    try:
        old_soft_list = old_data.get("Asset Details", {}).get("Software", [])
        new_soft_list = new_data.get("Asset Details", {}).get("Software", [])
        
        if isinstance(old_soft_list, list) and isinstance(new_soft_list, list):
            old_set = {f"{s.get('Name', 'Unknown')} {s.get('Version', '')}".strip() for s in old_soft_list if isinstance(s, dict)}
            new_set = {f"{s.get('Name', 'Unknown')} {s.get('Version', '')}".strip() for s in new_soft_list if isinstance(s, dict)}
            
            added = new_set - old_set
            removed = old_set - new_set
            
            for app in added:
                ChangeNotification.objects.create(
                    asset=asset,
                    field_name="Software Installed",
                    old_value="None",
                    new_value=app
                )
            for app in removed:
                ChangeNotification.objects.create(
                    asset=asset,
                    field_name="Software Removed",
                    old_value=app,
                    new_value="None"
                )
    except Exception as e:
        print(f"Diff error Software: {e}")

    # 3. Compare Processors
    try:
        old_cpu = old_data.get("Asset Details", {}).get("ComputerDetails", {}).get("Hardware", {}).get("Processors", {}).get("Name", "Unknown")
        new_cpu = new_data.get("Asset Details", {}).get("ComputerDetails", {}).get("Hardware", {}).get("Processors", {}).get("Name", "Unknown")
        
        if str(old_cpu) != str(new_cpu) and new_cpu != "Unknown":
            ChangeNotification.objects.create(
                asset=asset,
                field_name="Processor",
                old_value=str(old_cpu),
                new_value=str(new_cpu)
            )
    except Exception as e:
        print(f"Diff error Processor: {e}")
