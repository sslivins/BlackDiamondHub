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
                icon = entity['attributes'].get('icon', 'mdi:lightbulb')
                scenes.append({
                    "id": entity['entity_id'],
                    "name": entity['attributes'].get('friendly_name', entity['entity_id']),
                    "icon": homeassistant_icon_mapping(icon),  # Default icon if not found
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

def homeassistant_icon_mapping(hass_icon):
    """Map Home Assistant icons to Font Awesome icons."""
    icon_mapping = {
        "mdi:lightbulb": "fas fa-lightbulb",
        "mdi:movie": "fas fa-film",
        "mdi:television": "fas fa-tv",
        "mdi:silverware-fork-knife": "fas fa-utensils",
        "mdi:chef-hat": "fas fa-hat-chef",
    }
    
    fa_icon =  icon_mapping.get(hass_icon, "fas fa-question-circle")  # Default icon if not found
    
    if fa_icon == "fas fa-questionmark":
        print(f"Unsupported HomeAssistant icon: {hass_icon}")
        
    return fa_icon