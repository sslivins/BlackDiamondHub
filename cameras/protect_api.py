"""UniFi Protect API client for dynamic camera discovery."""

import logging
import time

import requests
import urllib3

from django.conf import settings

logger = logging.getLogger(__name__)

# Suppress InsecureRequestWarning for self-signed NVR certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Simple in-memory cache to avoid hitting the Protect API on every page load
_cache = {
    'cameras': None,
    'timestamp': 0,
}
CACHE_TTL = 300  # 5 minutes


def _camera_name_to_stream_name(name):
    """Convert a camera display name to a safe go2rtc stream name.

    E.g. "Front Door" -> "front_door", "Back-Yard Cam" -> "back_yard_cam"
    """
    return name.lower().replace(' ', '_').replace('-', '_')


def get_protect_cameras():
    """Fetch cameras from UniFi Protect API, with in-memory caching.

    Returns a list of dicts:
        [{'name': 'Front Door', 'stream_name': 'front_door',
          'rtsp_url': 'rtsps://host:7441/alias'}, ...]

    Returns an empty list on failure or if Protect is not configured.
    """
    now = time.time()
    if _cache['cameras'] is not None and (now - _cache['timestamp']) < CACHE_TTL:
        return _cache['cameras']

    cameras = _fetch_cameras_from_protect()
    if cameras is not None:
        _cache['cameras'] = cameras
        _cache['timestamp'] = now
    return cameras if cameras is not None else []


def clear_cache():
    """Clear the camera cache (useful for testing or manual refresh)."""
    _cache['cameras'] = None
    _cache['timestamp'] = 0


def _fetch_cameras_from_protect():
    """Authenticate with UniFi Protect and fetch all RTSP-enabled cameras.

    Returns a list of camera dicts, or None on failure.
    """
    host = getattr(settings, 'UNIFI_PROTECT_HOST', None)
    username = getattr(settings, 'UNIFI_PROTECT_USERNAME', None)
    password = getattr(settings, 'UNIFI_PROTECT_PASSWORD', None)

    if not all([host, username, password]):
        logger.warning("UniFi Protect credentials not configured")
        return None

    try:
        session = requests.Session()
        session.verify = False

        # Authenticate — returns TOKEN cookie and x-csrf-token header
        resp = session.post(
            f'https://{host}/api/auth/login',
            json={
                'username': username,
                'password': password,
                'rememberMe': False,
            },
            timeout=10,
        )
        resp.raise_for_status()

        csrf_token = resp.headers.get('x-csrf-token')
        if csrf_token:
            session.headers['x-csrf-token'] = csrf_token

        # Fetch bootstrap (contains NVR info + all cameras)
        resp = session.get(
            f'https://{host}/proxy/protect/api/bootstrap',
            timeout=15,
        )
        resp.raise_for_status()
        bootstrap = resp.json()

        rtsps_port = bootstrap.get('nvr', {}).get('ports', {}).get('rtsps', 7441)
        cameras_data = bootstrap.get('cameras', [])

        # Handle both list and dict formats
        if isinstance(cameras_data, dict):
            cameras_data = list(cameras_data.values())

        cameras = []
        for camera in cameras_data:
            name = camera.get('name', 'Unknown')
            cam_host = camera.get('connectionHost') or host

            # Find the first RTSP-enabled channel (highest quality first)
            rtsp_alias = None
            for channel in camera.get('channels', []):
                if channel.get('isRtspEnabled') and channel.get('rtspAlias'):
                    rtsp_alias = channel['rtspAlias']
                    break

            if rtsp_alias:
                cameras.append({
                    'name': name,
                    'stream_name': _camera_name_to_stream_name(name),
                    'rtsp_url': f'rtsps://{cam_host}:{rtsps_port}/{rtsp_alias}',
                })

        cameras.sort(key=lambda c: c['name'])
        return cameras

    except requests.RequestException as e:
        logger.error("Failed to fetch cameras from UniFi Protect: %s", e)
        return None
