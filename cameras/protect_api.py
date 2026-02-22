"""UniFi Protect API client for dynamic camera discovery.

Supports multiple Protect sites configured via UNIFI_PROTECT_SITES in settings.
Each site has: host, api_key, name.

Uses the UniFi Protect Integration (Public) API with API key auth.
- GET  /proxy/protect/integration/v1/cameras           — list cameras
- POST /proxy/protect/integration/v1/cameras/{id}/rtsps-stream — create RTSPS URL
- GET  /proxy/protect/integration/v1/cameras/{id}/rtsps-stream — get existing URL
Auth: X-API-KEY header
"""

import logging
import time

import requests
import urllib3

from django.conf import settings

logger = logging.getLogger(__name__)

# Suppress InsecureRequestWarning for self-signed NVR certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Per-site in-memory cache: {host: {'cameras': [...], 'timestamp': float}}
_cache = {}
CACHE_TTL = 300  # 5 minutes

API_BASE = '/proxy/protect/integration/v1'


def _camera_name_to_stream_name(name):
    """Convert a camera display name to a safe go2rtc stream name.

    E.g. "Front Door" -> "front_door", "Back-Yard Cam" -> "back_yard_cam"
    """
    return name.lower().replace(' ', '_').replace('-', '_')


def get_protect_cameras():
    """Fetch cameras from all configured UniFi Protect sites, with caching.

    Returns a list of site dicts:
        [{'name': 'Sun Peaks', 'cameras': [...]}, ...]

    Each camera dict has: name, camera_id, stream_name, rtsp_url,
    is_ptz, ptz_presets.
    Returns an empty list if no sites are configured.
    """
    sites = getattr(settings, 'UNIFI_PROTECT_SITES', [])
    if not sites:
        return []

    result = []
    now = time.time()

    for site in sites:
        host = site['host']
        api_key = site['api_key']
        site_name = site.get('name', host)

        # Check per-site cache
        cached = _cache.get(host)
        if cached and (now - cached['timestamp']) < CACHE_TTL:
            cameras = cached['cameras']
        else:
            cameras = _fetch_cameras_from_site(host, api_key)
            if cameras is not None:
                _cache[host] = {'cameras': cameras, 'timestamp': now}
            else:
                cameras = []

        result.append({
            'name': site_name,
            'host': host,
            'cameras': cameras,
        })

    return result


def clear_cache():
    """Clear the camera cache for all sites."""
    _cache.clear()


def _get_rtsps_url(host, api_key, camera_id):
    """Get or create an RTSPS stream URL for a camera.

    First tries GET to retrieve an existing stream. If none exists,
    creates one via POST with 'high' quality.

    Returns the RTSPS URL string, or None on failure.
    """
    base = f'https://{host}{API_BASE}/cameras/{camera_id}/rtsps-stream'
    headers = {'X-API-KEY': api_key}

    # Try to get existing RTSPS stream
    try:
        resp = requests.get(base, headers=headers, verify=False, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Return the highest quality available URL
        for quality in ('high', 'medium', 'low'):
            if data.get(quality):
                return _clean_rtsps_url(data[quality])
    except requests.RequestException:
        pass  # Fall through to create

    # No existing stream — create one
    try:
        resp = requests.post(
            base,
            headers={**headers, 'Content-Type': 'application/json'},
            json={'qualities': ['high']},
            verify=False,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        for quality in ('high', 'medium', 'low'):
            if data.get(quality):
                return _clean_rtsps_url(data[quality])
    except requests.RequestException as e:
        logger.warning("Failed to create RTSPS stream for camera %s: %s",
                       camera_id, e)

    return None


def _clean_rtsps_url(url):
    """Strip ?enableSrtp from RTSPS URLs — go2rtc handles TLS natively."""
    return url.split('?')[0] if url else url


def _is_ptz_camera(host, api_key, camera_id):
    """Detect if a camera supports PTZ by probing the goto endpoint.

    The Integration API doesn't expose PTZ feature flags, so we probe
    POST /v1/cameras/{id}/ptz/goto/0:
    - 204 = PTZ camera (moved to preset 0)
    - 400 = Not a PTZ camera ("Camera is not a type of PTZ")
    """
    url = f'https://{host}{API_BASE}/cameras/{camera_id}/ptz/goto/0'
    headers = {'X-API-KEY': api_key}

    try:
        resp = requests.post(url, headers=headers, verify=False, timeout=10)
        return resp.status_code == 204
    except requests.RequestException:
        return False


def _get_ptz_preset_count(host, api_key, camera_id):
    """Discover how many PTZ presets a camera has by probing slots 0-4.

    Returns the number of valid presets. Stops at the first 404
    ("Entity 'preset' not found").
    """
    headers = {'X-API-KEY': api_key}
    count = 0

    for slot in range(5):
        url = f'https://{host}{API_BASE}/cameras/{camera_id}/ptz/goto/{slot}'
        try:
            resp = requests.post(url, headers=headers, verify=False, timeout=10)
            if resp.status_code == 204:
                count += 1
            else:
                break
        except requests.RequestException:
            break

    return count


def ptz_goto_preset(camera_id, slot):
    """Move a PTZ camera to the given preset slot.

    Looks up the correct site by searching cached camera data.
    Returns True on success (204), False on failure.
    """
    # Find which site owns this camera
    host, api_key = _find_site_for_camera(camera_id)
    if not host:
        logger.warning("Camera %s not found in any configured site", camera_id)
        return False

    url = f'https://{host}{API_BASE}/cameras/{camera_id}/ptz/goto/{slot}'
    headers = {'X-API-KEY': api_key}

    try:
        resp = requests.post(url, headers=headers, verify=False, timeout=10)
        if resp.status_code == 204:
            logger.info("PTZ camera %s moved to preset %d", camera_id, slot)
            return True
        else:
            logger.warning("PTZ goto failed for camera %s slot %d: %d",
                           camera_id, slot, resp.status_code)
            return False
    except requests.RequestException as e:
        logger.error("PTZ goto request failed for camera %s: %s", camera_id, e)
        return False


def _find_site_for_camera(camera_id):
    """Find the site (host, api_key) that owns a camera_id.

    Searches cached camera data first. Returns (host, api_key) or (None, None).
    """
    sites = getattr(settings, 'UNIFI_PROTECT_SITES', [])

    # Search cache for the camera
    for site in sites:
        host = site['host']
        cached = _cache.get(host)
        if cached:
            for cam in cached['cameras']:
                if cam['camera_id'] == camera_id:
                    return host, site['api_key']

    # Not in cache — try all sites
    for site in sites:
        return site['host'], site['api_key']

    return None, None


def _fetch_cameras_from_site(host, api_key):
    """Fetch all cameras with RTSPS streams from a single Protect site.

    Uses API key authentication (X-API-KEY header). Discovers cameras via
    GET /v1/cameras, then fetches/creates RTSPS stream URLs for each.

    Returns a list of camera dicts, or None on failure.
    """
    if not all([host, api_key]):
        logger.warning("UniFi Protect not configured (need host and API key)")
        return None

    try:
        resp = requests.get(
            f'https://{host}{API_BASE}/cameras',
            headers={'X-API-KEY': api_key},
            verify=False,
            timeout=15,
        )
        resp.raise_for_status()
        cameras_data = resp.json()

        # Handle both list and dict formats
        if isinstance(cameras_data, dict):
            cameras_data = list(cameras_data.values())

        cameras = []
        for camera in cameras_data:
            name = camera.get('name', 'Unknown')
            camera_id = camera.get('id')
            if not camera_id:
                continue

            rtsp_url = _get_rtsps_url(host, api_key, camera_id)
            if rtsp_url:
                cam_info = {
                    'name': name,
                    'camera_id': camera_id,
                    'stream_name': _camera_name_to_stream_name(name),
                    'rtsp_url': rtsp_url,
                    'is_ptz': False,
                    'ptz_presets': 0,
                }

                # Probe for PTZ capability
                if _is_ptz_camera(host, api_key, camera_id):
                    cam_info['is_ptz'] = True
                    cam_info['ptz_presets'] = _get_ptz_preset_count(
                        host, api_key, camera_id,
                    )

                cameras.append(cam_info)

        cameras.sort(key=lambda c: c['name'])
        return cameras

    except requests.RequestException as e:
        logger.error("Failed to fetch cameras from UniFi Protect: %s", e)
        return None
