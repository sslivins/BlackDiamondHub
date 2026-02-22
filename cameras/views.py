import json
import logging
import urllib.request
import urllib.error
import urllib.parse

from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.http import require_POST

from .protect_api import get_protect_cameras, ptz_goto_preset

logger = logging.getLogger(__name__)


def get_go2rtc_streams(go2rtc_url):
    """Fetch the list of configured streams from go2rtc API.

    Used as a fallback when UniFi Protect is not configured — shows
    whatever streams are already registered in go2rtc (e.g. manually
    configured in go2rtc.yaml).
    """
    try:
        req = urllib.request.Request(f'{go2rtc_url}/api/streams')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            return [
                {
                    'name': name,
                    'display_name': name.replace('_', ' ').replace('-', ' ').title(),
                }
                for name in sorted(data.keys())
            ]
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to fetch streams from go2rtc at %s: %s", go2rtc_url, e)
        return []


def _register_streams_with_go2rtc(go2rtc_url, cameras):
    """Register camera RTSP streams with go2rtc via its API.

    Uses PATCH (upsert) so existing streams are updated and new ones created.
    Only registers streams that don't already exist in go2rtc.
    """
    # Fetch existing streams once
    try:
        req = urllib.request.Request(f'{go2rtc_url}/api/streams')
        with urllib.request.urlopen(req, timeout=5) as response:
            existing = set(json.loads(response.read()).keys())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        existing = set()

    for camera in cameras:
        if camera['stream_name'] in existing:
            continue
        try:
            src = urllib.parse.quote(camera['rtsp_url'], safe='')
            url = f"{go2rtc_url}/api/streams?name={camera['stream_name']}&src={src}"
            req = urllib.request.Request(url, method='PUT', data=b'')
            with urllib.request.urlopen(req, timeout=5):
                pass
        except (urllib.error.URLError, OSError) as e:
            logger.warning(
                "Failed to register stream %s with go2rtc: %s",
                camera['stream_name'], e,
            )


def camera_feed_view(request):
    """Display camera feeds via go2rtc, with tabs for multiple sites.

    If UniFi Protect sites are configured, cameras are discovered dynamically
    from each Protect API and registered with go2rtc on the fly.

    Falls back to showing whatever streams are already in go2rtc if
    no Protect sites are configured.
    """
    go2rtc_url = getattr(settings, 'GO2RTC_URL', 'http://localhost:1984')
    go2rtc_public_url = getattr(settings, 'GO2RTC_PUBLIC_URL', go2rtc_url)
    protect_sites = getattr(settings, 'UNIFI_PROTECT_SITES', [])

    if protect_sites:
        # Multi-site discovery via Protect API
        site_data = get_protect_cameras()
        sites = []
        for site in site_data:
            all_cameras = site.get('cameras', [])
            _register_streams_with_go2rtc(go2rtc_url, all_cameras)
            streams = [
                {
                    'name': cam['stream_name'],
                    'display_name': cam['name'],
                    'camera_id': cam.get('camera_id', ''),
                    'is_ptz': cam.get('is_ptz', False),
                    'ptz_presets': cam.get('ptz_presets', 0),
                    'preset_range': list(range(cam.get('ptz_presets', 0))),
                }
                for cam in all_cameras
            ]
            sites.append({
                'name': site['name'],
                'streams': streams,
            })
    else:
        # Fallback: show streams already configured in go2rtc
        streams = get_go2rtc_streams(go2rtc_url)
        sites = [{'name': 'Cameras', 'streams': streams}]

    return render(request, 'camera_feeds.html', {
        'sites': sites,
        'go2rtc_url': go2rtc_public_url,
    })


@require_POST
def ptz_goto(request):
    """AJAX endpoint to move a PTZ camera to a preset.

    Expects JSON body: {"camera_id": "...", "slot": 0}
    Returns JSON: {"success": true/false}
    """
    try:
        data = json.loads(request.body)
        camera_id = data.get('camera_id')
        slot = data.get('slot')

        if not camera_id or slot is None:
            return JsonResponse(
                {'success': False, 'error': 'Missing camera_id or slot'},
                status=400,
            )

        success = ptz_goto_preset(camera_id, int(slot))
        return JsonResponse({'success': success})

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=400,
        )
