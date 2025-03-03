from django.shortcuts import render, redirect
from django.conf import settings
import requests

# Home Assistant Configuration
HASS_URL = "http://homeassistant.local:8123"  # Update with your HA instance
HEADERS = {
    "Authorization": f"Bearer {settings.HOMEASSISTANT_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

def get_scenes():
    """Fetch the list of scenes from Home Assistant."""
    url = f"{HASS_URL}/api/states"
    response = requests.get(url, headers=HEADERS)
    scenes = []
    if response.status_code == 200:
        entities = response.json()
        for entity in entities:
            if entity['entity_id'].startswith('scene.'):
                scenes.append({
                    "id": entity['entity_id'],
                    "name": entity['attributes'].get('friendly_name', entity['entity_id']),
                    "icon": entity['attributes'].get('icon', '🖼️')  # Default icon if not provided
                })
    return scenes

def activate_scene(scene_id):
    """Activate a scene using Home Assistant API."""
    url = f"{HASS_URL}/api/services/scene/turn_on"
    data = {"entity_id": scene_id}
    requests.post(url, headers=HEADERS, json=data)

def scenes(request):
    """View to display and activate scenes."""
    if request.method == "POST":
        scene_id = request.POST.get("scene_id")
        if scene_id:
            activate_scene(scene_id)
        return redirect("scenes")  # Refresh page after activating scene

    scenes_list = get_scenes()
    return render(request, "scene_control.html", {"scenes": scenes_list})