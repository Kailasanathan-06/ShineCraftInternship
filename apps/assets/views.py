from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Asset, ScanResult
from .scanner_adapter import execute_scan


def asset_list_view(request):
    assets = Asset.objects.all().order_by("-last_scan")
    return render(request, "assets/asset_list.html", {"assets": assets})


def asset_detail_view(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    scans = ScanResult.objects.filter(asset=asset).order_by("-created_at")
    return render(request, "assets/asset_details.html", {
        "asset": asset,
        "scans": scans,
    })


from django.utils import timezone
import datetime
from django.core.cache import cache
from .diff_engine import detect_changes

@api_view(['GET'])
def agent_checkin(request, hostname):
    """
    Client agent periodically pings this endpoint.
    If 'scan_requested' is true for this asset, we return action='scan' (Manual override).
    Otherwise, we check the scheduled scan interval limit.
    """
    asset, created = Asset.objects.get_or_create(hostname=hostname)
    now = timezone.now()
    asset.last_checkin = now
    
    action = "idle"
    # 1. Manual Scan Check (No Limits)
    if asset.scan_requested:
        action = "scan"
    # 2. Scheduled Scan Check
    else:
        config = cache.get('auto_scan_config')
        if config and config.get('enabled'):
            last_scan = asset.last_scan
            interval = config.get('interval', 'daily')
            
            if not last_scan:
                action = "scan"
            else:
                elapsed = now - last_scan
                
                # Check limits based on schedule interval
                if interval == 'hourly' and elapsed >= datetime.timedelta(hours=1):
                    action = "scan"
                elif interval == 'daily' and elapsed >= datetime.timedelta(days=1):
                    action = "scan"
                elif interval == 'weekly' and elapsed >= datetime.timedelta(weeks=1):
                    action = "scan"
        
    asset.save()
    return Response({"action": action})

@api_view(['POST'])
def agent_upload(request):
    """
    Client agent posts the JSON scan payload here.
    """
    data = request.data
    asset_details = data.get("Asset Details", {})
    comp_details = asset_details.get("ComputerDetails", {}) if isinstance(asset_details, dict) else {}
    comp = comp_details.get("Computer system", {}) if isinstance(comp_details, dict) else {}
    hostname = comp.get("Name", "Unknown") if isinstance(comp, dict) else "Unknown"

    asset, created = Asset.objects.get_or_create(hostname=hostname)
    
    # Get previous scan data to compare
    previous_scan = ScanResult.objects.filter(asset=asset).order_by("-created_at").first()
    
    # Save new details
    asset.service_tag = comp.get("service tag") if isinstance(comp, dict) else None
    asset.manufacturer = comp.get("manufacturer", "") if isinstance(comp, dict) else ""
    asset.model = comp.get("model", "") if isinstance(comp, dict) else ""
    asset.assigned_user = comp.get("logged_in_user", "") if isinstance(comp, dict) else ""
    asset.last_checkin = timezone.now()
    asset.scan_requested = False  # clear the flag since it's done
    asset.save()

    # Create new scan result
    new_scan = ScanResult.objects.create(asset=asset, raw_output=data)

    # Trigger change detection
    if previous_scan:
        detect_changes(asset, previous_scan.raw_output, data)

    return Response({"status": "success", "message": f"Scan received for {hostname}"})

@method_decorator(csrf_exempt, name='dispatch')
class ManualScanAPIView(APIView):
    def post(self, request):
        # We no longer run it locally. We just queue the task for the remote agent.
        hostname = request.data.get("hostname")
        if not hostname:
            Asset.objects.all().update(scan_requested=True)
            return Response({
                "message": "Manual scan triggered! All online agents will begin scanning immediately.",
                "hostname": "All"
            })
            
        try:
            asset = Asset.objects.get(hostname=hostname)
            asset.scan_requested = True
            asset.save()
            return Response({
                "message": "Scan scheduled. The agent will run it upon next check-in.",
                "hostname": hostname
            })
        except Asset.DoesNotExist:
            return Response({"error": "Asset not found"}, status=404)