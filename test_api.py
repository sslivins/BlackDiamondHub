import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BlackDiamondHub.settings')
django.setup()

from cameras.protect_api import _fetch_cameras_from_protect

cameras = _fetch_cameras_from_protect()
if cameras:
    print(f"Found {len(cameras)} cameras:")
    for c in cameras:
        print(f"  - {c['name']} ({c['stream_name']})")
        print(f"    RTSP: {c['rtsp_url']}")
else:
    print("Failed or no cameras returned")
