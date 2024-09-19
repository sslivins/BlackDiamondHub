# sonos_control/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .views import get_sonos_speaker_info
import asyncio

class SonosConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print('WebSocket connected')
        await self.accept()
        self.speaker_group_name = 'sonos_speakers'

        # Add the WebSocket to the group
        await self.channel_layer.group_add(
            self.speaker_group_name,
            self.channel_name
        )

        # Start the task to send updates periodically
        self.send_task = asyncio.create_task(self.send_speaker_updates())

    async def disconnect(self, close_code):
        # Leave the group
        await self.channel_layer.group_discard(
            self.speaker_group_name,
            self.channel_name
        )

        # Cancel the periodic task
        self.send_task.cancel()

    async def receive(self, text_data):
        # You can handle messages from the client here if needed
        pass

    async def send_speaker_updates(self):
        while True:
            # Fetch the latest speaker info
            speakers_info = get_sonos_speaker_info()

            # Prepare data to send
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

            # Send the data to the WebSocket
            await self.send(text_data=json.dumps({
                'type': 'speaker_update',
                'speaker_data': speaker_data
            }))

            # Wait for 5 seconds before sending the next update
            await asyncio.sleep(5)
