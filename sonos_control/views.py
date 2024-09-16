from django.shortcuts import render, redirect
from django.http import JsonResponse
import soco
from django.templatetags.static import static
from soco.exceptions import SoCoUPnPException
from soco.plugins.sharelink import ShareLinkPlugin

import soco
from django.shortcuts import render

import soco
from django.shortcuts import render

def sonos_control_view(request):
    speakers_info = []

    # Discover all Sonos speakers on the network
    speakers = soco.discover()
    
    all_ungrouped_speakers = []
    
    if speakers:
        for speaker in speakers:
            #get list of speakers that are not part of any group
            if len(speaker.group.members) == 1:
                all_ungrouped_speakers.append(speaker)
        
        for speaker in speakers:
            # Get speaker info like current track, artist, album, volume, etc.
            current_track = speaker.get_current_track_info()
            queue = speaker.get_queue(full_album_art_uri=True)  # Fetch the speaker's queue
            
            #print(f'Speaker - {speaker.player_name} - is coordinator: {speaker.is_coordinator}: group label: {speaker.group.label}, this speaker {speaker} - group: {speaker.group}')
            
            # Prepare the queue list with album art
            queue_with_album_art = []
            for track in queue:
                # Get the album art URI, if available
                album_art_uri = track.album_art_uri if track.album_art_uri else None
                queue_with_album_art.append({
                    'title': track.title,
                    'artist': track.creator,  # Use 'creator' for the artist
                    'album_art': album_art_uri
                })
                
            #copy list of ungrouped speakers but remove the current speaker
            ungrouped_speakers = all_ungrouped_speakers.copy()
            try:
                ungrouped_speakers.remove(speaker)
            except ValueError:
                pass

            # Prepare information to pass to the template
            speaker_info = {
                'name': speaker.player_name,
                'uid': speaker.uid,
                'track': current_track['title'],
                'artist': current_track['artist'],
                'album': current_track['album'],
                'album_art': current_track['album_art'],
                'volume': speaker.volume,
                'play_state': speaker.get_current_transport_info()['current_transport_state'],
                'queue': queue_with_album_art,  # Include the queue with album art
                'is_coordinator': speaker.is_coordinator,
                'is_grouped': len(speaker.group.members) > 1,
                'group_label': speaker.group.label,
                'group': speaker.group.members,  # Get group members
                'ungrouped': ungrouped_speakers
            }
            speakers_info.append(speaker_info)

    context = {
        'speaker_info': speakers_info,
    }

    return render(request, 'sonos.html', context)


def toggle_group(request):
    if request.method == 'POST':
        speaker_uuid = request.POST.get('speaker_uuid')  # Get the UUID of the main speaker (coordinator)
        target_speaker_uuid = request.POST.get('target_speaker_uuid')  # Get the UUID of the target speaker

        # Get the action type (toggle_group)
        action = request.POST.get('action')

        if action != 'toggle_group':
            return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)

        # Discover the Sonos speakers
        speakers = soco.discover()
        if not speakers:
            return JsonResponse({'status': 'error', 'message': 'No speakers found'}, status=404)

        # Find the main speaker (coordinator) by UUID
        speaker = next((s for s in speakers if s.uid == speaker_uuid), None)
        if not speaker:
            return JsonResponse({'status': 'error', 'message': f'Speaker with UUID {speaker_uuid} not found'}, status=404)

        # Find the target speaker by UUID
        target_speaker = next((s for s in speakers if s.uid == target_speaker_uuid), None)
        if not target_speaker:
            return JsonResponse({'status': 'error', 'message': f'Target speaker with UUID {target_speaker_uuid} not found'}, status=404)

        # Toggle grouping: add the speaker to the group or remove from the group
        if target_speaker in speaker.group.members:
            # Remove target speaker from group
            target_speaker.unjoin()
            print(f'Target speaker {target_speaker_uuid} removed from speaker {speaker_uuid} group')
            return JsonResponse({'status': 'success', 'message': f'Target speaker {target_speaker_uuid} removed from speaker {speaker_uuid} group'})
        else:
            # Add target speaker to the group
            print(f'Adding target speaker {target_speaker_uuid} to speaker {speaker_uuid} group')
            speaker.join(target_speaker)
            return JsonResponse({'status': 'success', 'message': f'Target speaker {target_speaker_uuid} added to speaker {speaker_uuid} group'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)






def sonos_control(request):
    # Your speaker discovery logic
    speakers = []  # Populate this with your speaker information

    if request.method == 'POST':
        action = request.POST.get('action')
        speaker_name = request.POST.get('speaker_name')

        # Find the correct speaker using SoCo
        speaker = get_speaker_by_name(speaker_name)
        
        if action == 'play_spotify_uri':
            spotify_uri = request.POST.get('spotify_uri')
            try:
                # Play the Spotify URI on the Sonos speaker
                speaker.play_uri(spotify_uri)
                message = f"Playing {spotify_uri} on {speaker_name}"
            except SoCoUPnPException as e:
                message = f"Error: Could not play the URI: {e}"

            return JsonResponse({'status': 'success', 'message': message})
        elif action == 'volume':
            # Handle volume change logic here
            pass
        elif action == 'toggle_group':
            # Handle grouping logic here
            pass

    return render(request, 'your_template.html', {'speaker_info': speakers})

def get_speaker_by_name(name):
    # Function to discover speakers and return the one matching the name
    devices = soco.discover()
    for device in devices:
        if device.player_name == name:
            return device
    return None

import requests

def play_spotify_on_sonos(room_name, spotify_uri):
    sonos_api_url = f'http://<SONOS_API_SERVER>:5005/{room_name}/spotify/{spotify_uri}'
    
    try:
        response = requests.get(sonos_api_url)
        if response.status_code == 200:
            print(f'Successfully started playing {spotify_uri} on {room_name}')
        else:
            print(f'Failed to play track: {response.content}')
    except requests.RequestException as e:
        print(f'Error calling Sonos API: {e}')


def play_spotify_on_sonos(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        spotify_uri = request.POST.get('spotify_uri')
        
        print(f'Looking for speaker: {room_name}')
        
        # Find the Sonos speaker by name
        speakers = soco.discover()
        if speakers:
            speaker = next((s for s in speakers if s.player_name == room_name), None)
            if speaker:
                try:
                    share_link = ShareLinkPlugin(speaker)
                    # Stop any current playback first
                    print(f'Stopping current playback on {room_name}')
                    speaker.stop()
                    
                    share_link.add_share_link_to_queue('https://open.spotify.com/track/5Z01UMMf7V1o0MzF86s6WJ?si=a1a95142a3e249d8')
                    #index = share_link.add_share_link_to_queue('https://open.spotify.com/track/5bf3qVyRtIpk4Ym3JHalWk?si=af0cc1b567eb4631')
                    #print(f'Added Spotify URI to queue at index: {index}')
                    speaker.play_from_queue(index=1)
                    return redirect('success')
                except Exception as e:
                    print(f'Error while trying to play URI: {e}')
                    return render(request, 'error.html', {'error': f'Failed to play URI: {e}'})
            else:
                return render(request, 'error.html', {'error': 'Speaker not found'})
        else:
            return render(request, 'error.html', {'error': 'No Sonos speakers found'})
    
    context = {
        'spotify_uri': 'x-sonos-spotify:spotify%3atrack%3a5Z01UMMf7V1o0MzF86s6WJ?sid=9&flags=8224&sn=1',
        'room_name': 'Kitchen'
    }
    
    return render(request, 'play_spotify.html', context)



