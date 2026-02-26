"""
Home Assistant REST API client for device_control app.

Provides functions to fetch entity states and call services
(switch on/off, cover open/close, light on/off, etc.).
"""

import logging
import requests
from urllib.parse import urljoin
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 10  # seconds


def _headers():
    """Authorization headers for Home Assistant API."""
    return {
        "Authorization": f"Bearer {settings.HOMEASSISTANT_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def _base_url():
    """Home Assistant base URL."""
    return settings.HOMEASSISTANT_URL


def get_entity_state(entity_id):
    """
    Fetch the current state of a single entity.

    Returns dict with 'entity_id', 'state', and 'attributes',
    or None on failure.
    """
    url = urljoin(_base_url(), f"/api/states/{entity_id}")
    try:
        resp = requests.get(url, headers=_headers(), timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        logger.warning("HA returned %s for %s", resp.status_code, entity_id)
    except requests.RequestException as exc:
        logger.error("Failed to get state for %s: %s", entity_id, exc)
    return None


def get_entity_states(entity_ids):
    """
    Fetch states for multiple entities.

    Returns a dict mapping entity_id -> state dict.
    Fetches all states in a single call and filters.
    """
    url = urljoin(_base_url(), "/api/states")
    try:
        resp = requests.get(url, headers=_headers(), timeout=TIMEOUT)
        if resp.status_code == 200:
            all_states = resp.json()
            wanted = set(entity_ids)
            return {
                s["entity_id"]: s
                for s in all_states
                if s["entity_id"] in wanted
            }
        logger.warning("HA returned %s fetching all states", resp.status_code)
    except requests.RequestException as exc:
        logger.error("Failed to fetch states: %s", exc)
    return {}


def call_service(domain, service, entity_id, extra_data=None):
    """
    Call a Home Assistant service.

    Args:
        domain: e.g. 'switch', 'light', 'cover'
        service: e.g. 'turn_on', 'turn_off', 'toggle', 'open_cover', 'close_cover'
        entity_id: The entity to target
        extra_data: Optional dict of additional service data

    Returns:
        (success: bool, error: str or None)
    """
    url = urljoin(_base_url(), f"/api/services/{domain}/{service}")
    payload = {"entity_id": entity_id}
    if extra_data:
        payload.update(extra_data)

    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=TIMEOUT)
        if resp.status_code == 200:
            return True, None
        msg = f"HA returned {resp.status_code}: {resp.text[:200]}"
        logger.warning(msg)
        return False, msg
    except requests.RequestException as exc:
        msg = f"Request failed: {exc}"
        logger.error(msg)
        return False, msg
