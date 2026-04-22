from django.shortcuts import render
from ShineCraftInternship.apps.assets.models import Asset
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
import json


from ShineCraftInternship.apps.notifications.models import ChangeNotification

def dashboard_home(request):
    all_assets = Asset.objects.all()
    total_assets = all_assets.count()
    online_assets = sum(1 for asset in all_assets if asset.is_online)
    
    recent_changes = ChangeNotification.objects.all().order_by("-created_at")[:10]

    return render(request, "dashboard/index.html", {
        "total_assets": total_assets,
        "online_assets": online_assets,
        "recent_changes": recent_changes,
    })


@method_decorator(csrf_exempt, name='dispatch')
class ScheduleAutoScanAPIView(APIView):
    """Handle automatic scan scheduling"""
    def post(self, request):
        try:
            data = json.loads(request.body)
            interval = data.get('interval', 'daily')  # daily, weekly, hourly
            time = data.get('time', '02:00')  # time in HH:MM format
            
            # Store the schedule configuration
            from django.core.cache import cache
            cache.set('auto_scan_config', {
                'enabled': True,
                'interval': interval,
                'time': time
            }, None)  # Store indefinitely
            
            return Response({
                "message": f"Automatic scan scheduled {interval} at {time}",
                "status": "scheduled"
            })
        except Exception as e:
            return Response({
                "message": f"Error scheduling scan: {str(e)}",
                "status": "error"
            }, status=400)

    def get(self, request):
        """Get current schedule configuration"""
        try:
            from django.core.cache import cache
            config = cache.get('auto_scan_config')
            if config:
                return Response(config)
            return Response({
                "enabled": False,
                "message": "No automatic scan scheduled"
            })
        except Exception as e:
            return Response({
                "message": f"Error fetching schedule: {str(e)}",
                "status": "error"
            }, status=400)