import json
import logging
import urllib.request
import urllib.error
import urllib.parse

from django.shortcuts import render
from django.conf import settings

from .protect_api import get_protect_cameras

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
    """Display camera feeds via go2rtc.

    If UniFi Protect is configured, cameras are discovered dynamically
    from the Protect API and registered with go2rtc on the fly.

    Falls back to showing whatever streams are already in go2rtc if
    Protect is not configured.
    """
    go2rtc_url = getattr(settings, 'GO2RTC_URL', 'http://localhost:1984')
    protect_host = getattr(settings, 'UNIFI_PROTECT_HOST', '')

    if protect_host:
        # Dynamic discovery via Protect API
        cameras = get_protect_cameras()
        _register_streams_with_go2rtc(go2rtc_url, cameras)
        streams = [
            {'name': cam['stream_name'], 'display_name': cam['name']}
            for cam in cameras
        ]
    else:
        # Fallback: show streams already configured in go2rtc
        streams = get_go2rtc_streams(go2rtc_url)

    return render(request, 'camera_feeds.html', {
        'streams': streams,
        'go2rtc_url': go2rtc_url,
    })
