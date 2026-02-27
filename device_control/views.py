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

from .device_config import TABS, get_all_entity_ids
from .ha_client import call_service, get_entity_states

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
