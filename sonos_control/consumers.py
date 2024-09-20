# sonos_control/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .views import get_sonos_speaker_info, adjust_speaker_volume
import asyncio

class SonosConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.speaker_group_name = 'sonos_speakers'

        # Add the WebSocket to the group
        await self.channel_layer.group_add(
            self.speaker_group_name,
            self.channel_name
        )

        # Initialize the previous state to None
        self.previous_speaker_data = None

        # Start the task to send updates periodically, only if not already running
        if not hasattr(self, 'send_task') or self.send_task.done():
            self.send_task = asyncio.create_task(self.send_speaker_updates())

    async def disconnect(self, close_code):
        # Leave the group
        await self.channel_layer.group_discard(
            self.speaker_group_name,
            self.channel_name
        )

        # Cancel the periodic task if it exists
        if hasattr(self, 'send_task') and not self.send_task.done():
            try:
                self.send_task.cancel()
            except asyncio.CancelledError:
                pass

    async def receive(self, text_data):
        # Parse the incoming WebSocket message (which is a JSON string)
        data = json.loads(text_data)
        
        # Extract the relevant fields from the data
        speaker_name = data.get('speaker_name')
        volume = data.get('volume')
        action = data.get('action')
        
        if action == 'volume':
            # Call the shared function to adjust the volume
            result = adjust_speaker_volume(speaker_name, volume)

            # Send the result back to the WebSocket client
            await self.send(text_data=json.dumps({
                'status': result['status'],
                'message': result.get('message'),
                'volume': result.get('volume')
            }))
        else:
            await self.send(text_data=json.dumps({
                'status': 'error',
                'message': 'Unknown action'
            }))

    async def send_speaker_updates(self):
        while True:
            # Fetch the latest speaker info
            speakers_info = get_sonos_speaker_info()

            # Prepare the new data to send
            speaker_data = {}
            for info in speakers_info:
                if info['is_coordinator']:
                    speaker_data[info['uid']] = {
                        'track': info['track'],
                        'artist': info['artist'],
                        'album': info['album'],
                        'volume': info['volume'],
                        'play_state': info['play_state'],
                        'album_art': info['album_art'],
                        'queue': info['queue']
                    }

            # Check if the data has changed
            if speaker_data != self.previous_speaker_data:
                # Data has changed, send it to the WebSocket
                await self.send(text_data=json.dumps({
                    'type': 'speaker_update',
                    'speaker_data': speaker_data
                }))
                # Update the previous state
                self.previous_speaker_data = speaker_data

            # Wait for 5 seconds before checking again
            await asyncio.sleep(3)
            
    async def adjust_speaker_volume(self, speaker_name, volume):
        # This function should contain the logic to adjust the speaker's volume
        # using your existing Sonos integration or other systems.
        
        # Placeholder logic: Just print for now
        print(f"Adjusting {speaker_name}'s volume to {volume}")
        
        # Here you'd add the actual volume adjustment logic, for example:
        # speaker = get_speaker_by_name(speaker_name)
        # speaker.set_volume(volume)
        # Adjust this according to your Sonos control logic            
