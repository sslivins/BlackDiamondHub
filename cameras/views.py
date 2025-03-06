from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
import json
import asyncio
import websockets
from urllib.parse import urljoin

async def get_camera_feeds_ws(authenticated=False):
    """Fetch the list of camera entities and extract HLS stream URLs using WebSocket API."""
    camera_feeds = []
    instance_index = 1
    request_id = 1

    while True:
        if instance_index == 1:
            base_url = getattr(settings, 'HOMEASSISTANT_URL', None)
            access_token = getattr(settings, 'HOMEASSISTANT_ACCESS_TOKEN', None)
        else:
            if not authenticated:
                break
            base_url = getattr(settings, f'HOMEASSISTANT_URL_{instance_index}', None)
            access_token = getattr(settings, f'HOMEASSISTANT_ACCESS_TOKEN_{instance_index}', None)

        if not base_url or not access_token:
            break

        ws_url = urljoin(base_url.replace("http", "ws"), "/api/websocket")
        
        try:
            async with websockets.connect(ws_url) as websocket:

                #should receive an message type of auth_required
                auth_required_message = await websocket.recv()
                auth_required = json.loads(auth_required_message)
                print("Auth required message:", auth_required)
                
                if auth_required.get("type") != "auth_required":
                    print("Unexpected message:", auth_required)
                    break
                
                # Send authentication message 
                auth_message = {
                    "type": "auth",
                    "access_token": access_token
                }
                await websocket.send(json.dumps(auth_message))
                # Wait for authentication response
                auth_response_message = await websocket.recv()
                
                auth_response = json.loads(auth_response_message)
                
                if auth_response.get("type") != "auth_ok":
                    print("Authentication failed:", auth_response)
                    break

                # Request all states
                await websocket.send(json.dumps({
                    "id": request_id,
                    "type": "get_states"
                }))
                request_id += 1
                
                state_response = await websocket.recv()
                states = json.loads(state_response)

                # Iterate through cameras
                for entity in states.get("result", []):
                    if entity["entity_id"].startswith("camera."):
                        camera_entity_id = entity["entity_id"]

                        # Request HLS Stream
                        stream_url = await get_hls_stream_ws(websocket, request_id, camera_entity_id)
                        request_id += 1

                        if stream_url:
                            camera_feeds.append({
                                "name": entity["attributes"].get("friendly_name", camera_entity_id),
                                "url": urljoin(base_url,stream_url),
                            })

        except Exception as e:
            print(f"WebSocket Error: {e}")

        instance_index += 1

    return camera_feeds


async def get_hls_stream_ws(websocket, request_id, camera_entity_id):
    """Request an HLS stream URL for a given camera entity via WebSocket."""
    request = {
        "id": request_id,
        "type": "camera/stream",
        "entity_id": camera_entity_id,
        "format": "hls"
    }

    await websocket.send(json.dumps(request))
    response = await websocket.recv()
    stream_data = json.loads(response)

    #print(f"Stream response for {camera_entity_id}: {stream_data}")  # Debugging line to check the response

    if "result" in stream_data:
        return stream_data["result"].get("url")
    else:
        print(f"Failed to get HLS stream for {camera_entity_id}: {stream_data}")
        return None


def camera_feed_view(request):
    """View to display camera feeds."""
    authenticated = request.user.is_authenticated
    camera_feeds = asyncio.run(get_camera_feeds_ws(authenticated=authenticated))

    #print(f"Camera feeds: {camera_feeds}")  # Debugging line to check the fetched camera feeds

    return render(request, "camera_feeds.html", {"camera_feeds": camera_feeds})
