from django.shortcuts import render, redirect
from django.conf import settings
import requests

# Home Assistant Configuration
HASS_URL = "http://homeassistant.local:8123"  # Update with your HA instance
ENTITY_ID = "light.office_ceiling_over_couch"
HEADERS = {
    "Authorization": f"Bearer {settings.HOMEASSISTANT_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

def get_light_state():
    """Fetch the current state of the light from Home Assistant."""
    url = f"{HASS_URL}/api/states/{ENTITY_ID}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("state")
    return None

def toggle_light():
    """Toggle the light using Home Assistant API."""
    state = get_light_state()
    if state == "on":
        url = f"{HASS_URL}/api/services/light/turn_off"
    else:
        url = f"{HASS_URL}/api/services/light/turn_on"
    data = {"entity_id": ENTITY_ID}
    requests.post(url, headers=HEADERS, json=data)

def scenes(request):
    """View to display the light status and toggle it."""
    if request.method == "POST":
        toggle_light()
        return redirect("scenes")  # Refresh page after toggling

    light_state = get_light_state()
    return render(request, "scene_control.html", {"light_state": light_state})