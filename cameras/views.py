from django.shortcuts import render
from django.conf import settings
import requests

def get_camera_feeds():
    """Fetch the list of camera entities from Home Assistant and extract the entity_picture URL."""
    HASS_URL = "http://homeassistant.local:8123"  # Update with your HA instance
    HEADERS = {
        "Authorization": f"Bearer {settings.HOMEASSISTANT_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    url = f"{HASS_URL}/api/states"
    response = requests.get(url, headers=HEADERS)
    camera_feeds = []
    if response.status_code == 200:
        entities = response.json()
        for entity in entities:
            if entity['entity_id'].startswith('camera.'):
                entity_picture = entity['attributes'].get('entity_picture')
                if entity_picture:
                    camera_feeds.append({
                        "name": entity['attributes'].get('friendly_name', entity['entity_id']),
                        "url": f"{HASS_URL}{entity_picture}"
                    })
    return camera_feeds

def camera_feed_view(request):
    """View to display camera feeds."""
    camera_feeds = get_camera_feeds()
    
    print(f"Camera feeds: {camera_feeds}")  # Debugging line to check the fetched camera feeds
    
    return render(request, 'cameras/camera_feeds.html', {'camera_feeds': camera_feeds})