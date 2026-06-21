"""
Views for the device_control app.

Provides:
  - device_control_view: renders the main page shell with tabs
  - device_control_states: AJAX endpoint returning current entity states as JSON
  - device_control_action: AJAX endpoint to toggle/control a device
"""

import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .device_config import TABS, get_all_entity_ids, FIREPLACE_OVERRIDES, GEMSTONE_OVERRIDES
from .ha_client import call_service, get_entity_states
from . import napoleon_client
from . import gemstone_client

logger = logging.getLogger(__name__)

# Maps device type to the HA domain / service names
SERVICE_MAP = {
    "switch": {
        "on": ("switch", "turn_on"),
        "off": ("switch", "turn_off"),
        "toggle": ("switch", "toggle"),
    },
    "light": {
        "on": ("light", "turn_on"),
        "off": ("light", "turn_off"),
        "toggle": ("light", "toggle"),
    },
    "cover": {
        "open": ("cover", "open_cover"),
        "close": ("cover", "close_cover"),
        "stop": ("cover", "stop_cover"),
        "set_position": ("cover", "set_cover_position"),
    },
    "media_player": {
        "on": ("media_player", "turn_on"),
        "off": ("media_player", "turn_off"),
        "toggle": ("media_player", "toggle"),
    },
}


def device_control_view(request):
    """Render the device control page shell with tab definitions."""
    return render(request, "device_control/device_control.html", {"tabs": TABS})


def device_control_states(request):
    """
    AJAX endpoint: fetch current states for all configured entities.

    Returns JSON: { entity_id: { state, friendly_name, current_position? } }
    """
    all_ids = get_all_entity_ids()
    raw_states = get_entity_states(all_ids)

    result = {}
    for eid, data in raw_states.items():
        attrs = data.get("attributes", {})
        entry = {
            "state": data.get("state", "unknown"),
            "friendly_name": attrs.get("friendly_name", eid),
        }
        # Include position for covers
        pos = attrs.get("current_position")
        if pos is not None:
            entry["current_position"] = pos
        # Include brightness info for lights
        brightness = attrs.get("brightness")
        if brightness is not None:
            entry["brightness"] = brightness  # 0-255
        color_modes = attrs.get("supported_color_modes")
        if color_modes:
            entry["supported_color_modes"] = color_modes
        result[eid] = entry

    return JsonResponse(result)


@require_POST
def device_control_action(request):
    """
    AJAX endpoint: perform an action on a device.

    Expects JSON body: { entity_id, action, type }
      - entity_id: e.g. "switch.living_room_tv_socket_1"
      - action: e.g. "on", "off", "toggle", "open", "close", "stop"
      - type: e.g. "switch", "light", "cover", "media_player"
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    entity_id = body.get("entity_id", "")
    action = body.get("action", "")
    device_type = body.get("type", "")

    # Validate entity is in our config
    allowed = get_all_entity_ids()
    if entity_id not in allowed:
        return JsonResponse({"error": "Entity not allowed"}, status=403)

    # Look up the service call
    type_map = SERVICE_MAP.get(device_type)
    if not type_map:
        return JsonResponse({"error": f"Unknown device type: {device_type}"}, status=400)

    service_info = type_map.get(action)
    if not service_info:
        return JsonResponse({"error": f"Unknown action: {action}"}, status=400)

    domain, service = service_info

    # Pass brightness for light dimming
    extra_data = None
    if device_type == "light" and action == "on":
        brightness = body.get("brightness")
        if brightness is not None:
            extra_data = {"brightness": int(brightness)}
    elif device_type == "cover" and action == "set_position":
        position = body.get("position")
        if position is not None:
            extra_data = {"position": int(position)}

    success, error = call_service(domain, service, entity_id, extra_data=extra_data)

    if success:
        return JsonResponse({"ok": True, "entity_id": entity_id, "action": action})
    else:
        return JsonResponse({"ok": False, "error": error}, status=502)


# ──────────────────────────────────────────────
# Fireplace (Napoleon cloud) endpoints
# ──────────────────────────────────────────────
# These bypass Home Assistant entirely and talk to the Napoleon (Ayla) cloud
# through device_control.napoleon_client. Validation of action names is done
# against the bridge's own action map.

# Action -> validator for the supplied value. Anything not listed is rejected.
_FIREPLACE_ACTION_VALIDATORS = {
    "power": lambda v: isinstance(v, bool),
    "flame_speed": lambda v: isinstance(v, int) and 1 <= v <= 5,
    "orange_flame": lambda v: isinstance(v, int) and 0 <= v <= 4,
    "yellow_flame": lambda v: isinstance(v, int) and 0 <= v <= 4,
    "heater": lambda v: v in (0, 1, 2),
    "setpoint_c": lambda v: isinstance(v, int) and 18 <= v <= 30,
    "eco_mode": lambda v: isinstance(v, bool),
    "boost_mode": lambda v: isinstance(v, bool),
    "ember_bed_rgb": lambda v: _is_rgb(v),
    "ember_bed_brightness": lambda v: isinstance(v, int) and 0 <= v <= 4,
    "ember_bed_cycling": lambda v: isinstance(v, bool),
    "top_light_rgb": lambda v: _is_rgb(v),
    "top_light_cycling": lambda v: isinstance(v, bool),
    "favourite": lambda v: v in (
        "partytime",
        "campfirewarmth",
        "summerday",
        "glowingsunset",
    ),
}


def _is_rgb(v):
    return (
        isinstance(v, (list, tuple))
        and len(v) == 3
        and all(isinstance(c, int) and 0 <= c <= 255 for c in v)
    )


def _apply_overrides(state):
    """Apply optional name/room overrides from device_config to a state dict."""
    override = FIREPLACE_OVERRIDES.get(state.get("dsn"))
    if override:
        if override.get("name"):
            state["name"] = override["name"]
        if override.get("room"):
            state["room"] = override["room"]
    return state


def device_control_fireplace_states(request):
    """AJAX endpoint: current state of every discovered fireplace.

    Returns JSON: { "configured": bool, "fireplaces": [ {...}, ... ] }
    """
    if not napoleon_client.is_configured():
        return JsonResponse({"configured": False, "fireplaces": []})

    try:
        states = napoleon_client.get_states()
    except napoleon_client.FireplaceError as exc:
        logger.warning("Fireplace states fetch failed: %s", exc)
        return JsonResponse({"configured": True, "error": str(exc)}, status=502)

    states = [_apply_overrides(s) for s in states]
    return JsonResponse({"configured": True, "fireplaces": states})


@require_POST
def device_control_fireplace_action(request):
    """AJAX endpoint: apply a control action to a fireplace.

    Expects JSON body: { dsn, action, value }
    Returns the refreshed fireplace state on success.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    dsn = body.get("dsn", "")
    action = body.get("action", "")
    value = body.get("value")

    if not dsn:
        return JsonResponse({"error": "Missing dsn"}, status=400)

    validator = _FIREPLACE_ACTION_VALIDATORS.get(action)
    if validator is None:
        return JsonResponse({"error": f"Unknown action: {action}"}, status=400)
    if not validator(value):
        return JsonResponse(
            {"error": f"Invalid value for {action}: {value!r}"}, status=400
        )

    if not napoleon_client.is_configured():
        return JsonResponse({"error": "Napoleon not configured"}, status=503)

    try:
        state = napoleon_client.apply_action(dsn, action, value)
    except napoleon_client.FireplaceError as exc:
        logger.warning("Fireplace action %s failed: %s", action, exc)
        return JsonResponse({"ok": False, "error": str(exc)}, status=502)

    return JsonResponse({"ok": True, "fireplace": _apply_overrides(state)})


# ──────────────────────────────────────────────
# Gemstone Lights (cloud) endpoints
# ──────────────────────────────────────────────
# These bypass Home Assistant entirely and talk to the Gemstone Lights cloud
# through device_control.gemstone_client. The control surface is intentionally
# small: power on/off and selecting one of the user's saved patterns.

# Action -> validator for the supplied value. Anything not listed is rejected.
_GEMSTONE_ACTION_VALIDATORS = {
    "power": lambda v: isinstance(v, bool),
    "pattern": lambda v: isinstance(v, str) and bool(v),
}


def _apply_gemstone_overrides(state):
    """Apply optional name/room overrides from device_config to a state dict."""
    override = GEMSTONE_OVERRIDES.get(state.get("id"))
    if override:
        if override.get("name"):
            state["name"] = override["name"]
        if override.get("room"):
            state["room"] = override["room"]
    return state


def device_control_gemstone_states(request):
    """AJAX endpoint: current state of every Gemstone device + saved patterns.

    Returns JSON: { "configured": bool, "devices": [...], "patterns": [...] }
    """
    if not gemstone_client.is_configured():
        return JsonResponse({"configured": False, "devices": [], "patterns": []})

    try:
        data = gemstone_client.get_states()
    except gemstone_client.GemstoneError as exc:
        logger.warning("Gemstone states fetch failed: %s", exc)
        return JsonResponse({"configured": True, "error": str(exc)}, status=502)

    devices = [_apply_gemstone_overrides(d) for d in data.get("devices", [])]
    return JsonResponse(
        {
            "configured": True,
            "devices": devices,
            "patterns": data.get("patterns", []),
        }
    )


@require_POST
def device_control_gemstone_action(request):
    """AJAX endpoint: apply a control action to a Gemstone device.

    Expects JSON body: { device_id, action, value }
    Returns the refreshed device state on success.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    device_id = body.get("device_id", "")
    action = body.get("action", "")
    value = body.get("value")

    if not device_id:
        return JsonResponse({"error": "Missing device_id"}, status=400)

    validator = _GEMSTONE_ACTION_VALIDATORS.get(action)
    if validator is None:
        return JsonResponse({"error": f"Unknown action: {action}"}, status=400)
    if not validator(value):
        return JsonResponse(
            {"error": f"Invalid value for {action}: {value!r}"}, status=400
        )

    if not gemstone_client.is_configured():
        return JsonResponse({"error": "Gemstone not configured"}, status=503)

    try:
        state = gemstone_client.apply_action(device_id, action, value)
    except gemstone_client.GemstoneError as exc:
        logger.warning("Gemstone action %s failed: %s", action, exc)
        return JsonResponse({"ok": False, "error": str(exc)}, status=502)

    return JsonResponse({"ok": True, "device": _apply_gemstone_overrides(state)})
