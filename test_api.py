import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BlackDiamondHub.settings')
django.setup()

from cameras.protect_api import get_protect_cameras

sites = get_protect_cameras()
if sites:
    for site in sites:
        print(f"\n{site['name']} ({site['host']}):")
        for c in site['cameras']:
            print(f"  - {c['name']} ({c['stream_name']})")
            print(f"    RTSP: {c['rtsp_url']}")
            if c.get('is_ptz'):
                print(f"    PTZ: {c['ptz_presets']} presets")
else:
    print("No sites configured")
