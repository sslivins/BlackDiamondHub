from django.shortcuts import render, redirect
from django.http import JsonResponse
import soco
from django.templatetags.static import static
from soco.exceptions import SoCoUPnPException
from soco.plugins.sharelink import ShareLinkPlugin
from soco.plugins.sharelink import SpotifyShare
import json
from django.http import JsonResponse
import spotipy
from social_django.models import UserSocialAuth
import time
from datetime import datetime
from social_django.utils import load_strategy

def sonos_control_view(request):
    speakers_info = get_sonos_speaker_info()

    context = {
        'speaker_info': speakers_info,
    }

    return render(request, 'sonos.html', context)

def get_sonos_status_partial(request):
    speakers_info = get_sonos_speaker_info()

    # Render the partial HTML for the speakers
    rendered_html = render(request, 'partials/sonos_speakers.html', {'speaker_info': speakers_info})

    return JsonResponse({'status': 'success', 'html': rendered_html.content.decode('utf-8')})


def toggle_group(request):
    if request.method == 'POST':
        speaker_uuid = request.POST.get('speaker_uuid')  # Get the UUID of the main speaker (coordinator)
        target_speakers_uuid = request.POST.getlist('target_speaker_uuid[]')  # Get the UUID of the target speaker
        
        print(f'target_speakers_uuid: {target_speakers_uuid}')

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

        status = []
        
        # Find the target speaker by UUID
        for target_uid in target_speakers_uuid:
            target_speaker = next((s for s in speakers if s.uid == target_uid), None)
            if not target_speaker:
                return JsonResponse({'status': 'error', 'message': f'Target speaker with UID {target_uid} not found'}, status=404)

            # Toggle grouping: add the speaker to the group or remove from the group
            if target_speaker in speaker.group.members:
                # Remove target speaker from group
                target_speaker.unjoin()
                print(f'Target speaker {target_uid} removed from speaker {speaker_uuid} group')
                status.append({'status': 'success', 'message': f'Target speaker {target_uid} removed from speaker {speaker_uuid} group'})
            else:
                # Add target speaker to the group
                target_speaker.join(speaker)                
                print(f'Adding target speaker {target_speaker.player_name}:{target_uid} to speaker {speaker.player_name}:{speaker_uuid} group')
                status.append({'status': 'success', 'message': f'Target speaker {target_uid} added to speaker {speaker_uuid} group'})
                
        
        return JsonResponse({'status': 'success', 'message': status})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

from django.http import JsonResponse
import soco

def adjust_volume(request):
    if request.method == 'POST':
        speaker_uid = request.POST.get('speaker_name')  # Get the speaker UID from the form data
        volume = request.POST.get('volume')  # Get the volume from the form data

        # Call the shared function to adjust the volume
        result = adjust_speaker_volume(speaker_uid, volume)

        # Return the result as a JsonResponse
        return JsonResponse({
            'status': result['status'],
            'message': result.get('message'),
            'volume': result.get('volume')
        }, status=result['status_code'])
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


def adjust_speaker_volume(speaker_uid, volume):
    """
    Adjusts the volume for a specific speaker by its UID.
    Returns a dictionary with the status and message.
    """
    if not speaker_uid or not volume:
        return {'status': 'error', 'message': 'Invalid parameters', 'status_code': 400}

    # Discover Sonos speakers
    speakers = soco.discover()
    if not speakers:
        return {'status': 'error', 'message': 'No Sonos speakers found', 'status_code': 404}

    # Find the speaker by its UID
    speaker = next((s for s in speakers if s.uid == speaker_uid), None)
    if not speaker:
        return {'status': 'error', 'message': f'Speaker {speaker_uid} not found', 'status_code': 404}

    try:
        # Adjust the speaker's volume
        speaker.volume = int(volume)
        return {'status': 'success', 'volume': speaker.volume, 'status_code': 200}
    except Exception as e:
        return {'status': 'error', 'message': f'Failed to adjust volume: {str(e)}', 'status_code': 500}


def speaker_play_pause(speaker_uid, action, track_index=None):
    """
    Handles toggling play/pause for a speaker by UID.
    Returns a dictionary with the status and message.
    """
    if not speaker_uid or not action:
        return {'status': 'error', 'message': 'Invalid parameters', 'status_code': 400}

    # Discover Sonos speakers
    speakers = soco.discover()
    if not speakers:
        return {'status': 'error', 'message': 'No Sonos speakers found', 'status_code': 404}

    # Find the speaker by its UID
    speaker = next((s for s in speakers if s.uid == speaker_uid), None)
    if not speaker:
        return {'status': 'error', 'message': f'Speaker {speaker_uid} not found', 'status_code': 404}

    try:
        # Perform play or pause based on the action
        if action == 'play':
            speaker.play()
        elif action == 'pause':
            speaker.pause()
        elif action == 'play_track':
            speaker.play_from_queue(int(track_index))
        else:
            return {'status': 'error', 'message': 'Invalid action', 'status_code': 400}

        return {'status': 'success', 'message': f'The Operation Completed Successfully', 'action': action, 'status_code': 200}
    except Exception as e:
        return {'status': 'error', 'message': f'Failed to toggle play/pause: {str(e)}', 'status_code': 500}


def toggle_play_pause(request):
    if request.method == 'POST':
        speaker_uid = request.POST.get('speaker_name')  # Get the speaker UID from the form data
        action = request.POST.get('action')  # Get the action (play or pause) from the form data

        # Call the shared function to handle play/pause
        result = speaker_play_pause(speaker_uid, action)

        # Return the result as a JsonResponse
        return JsonResponse({
            'status': result['status'],
            'message': result.get('message'),
            'action': result.get('action')
        }, status=result['status_code'])

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def queue_track(request):
    if request.method == 'POST':
        speakerUid = request.POST.get('speakerUid')
        service = request.POST.get('service')
        track_uri = request.POST.get('track_uri')
        position = request.POST.get('position')
        
        print(f'Looking for speaker: {speakerUid} - adding track: {track_uri} at position: {position}')
        
        # Find the Sonos speaker by name
        speakers = soco.discover()
        if speakers:
            speaker = next((s for s in speakers if s.uid == speakerUid), None)
            if speaker:
                try:
                    share_link_plugin = ShareLinkPlugin(speaker)
                    queue_position = 0 # Add to the end of the queue
                    if position == 'next':
                        queue_position = 1; # Add to the end of the queue                    
                    insert_index = share_link_plugin.add_share_link_to_queue(uri=track_uri, position=queue_position)
                    print(f'Added Spotify URI to queue at index: {insert_index}')
                    return JsonResponse({'status': 'success', 'message': f'Track added to queue on {speakerUid}'})
                except Exception as e:
                    print(f'Error while trying to play URI: {e}')
                    return JsonResponse({'status': 'error', 'message': f'Failed to add track to queue: {e}'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Speaker not found'})
        else:
            return JsonResponse({'status': 'error', 'message': 'No Sonos speakers found'})
    
   
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def play_uri(request):
    if request.method == 'POST':
        speakerUid = request.POST.get('speakerUid')
        service = request.POST.get('service')
        track_uri = request.POST.get('track_uri')
        
        print(f'Looking for speaker: {speakerUid}')
        
        # Find the Sonos speaker by name
        speakers = soco.discover()
        if speakers:
            speaker = next((s for s in speakers if s.uid == speakerUid), None)
            if speaker:
                try:
                    share_link_plugin = ShareLinkPlugin(speaker)
                    # if service == 'spotify':
                    #     print(f'is uri a share link: {share_link_plugin.is_share_link(track_uri)}')
                    #     spotify_share = SpotifyShare()
                    #     share_uri = spotify_share.canonical_uri(track_uri)
                    #     print(f'Adding Spotify URI to queue: {share_uri}')
                    # else:
                    #     return JsonResponse({'status': 'error', 'message': 'Invalid service'}, status=400)
                    
                    speaker.stop()
                    insert_index = share_link_plugin.add_share_link_to_queue(uri=track_uri, position=1)
                    print(f'Added Spotify URI to queue at index: {insert_index}')
                    speaker.play_from_queue(index=insert_index-1)
                    return JsonResponse({'status': 'success', 'message': f'Playing track {track_uri} on {speakerUid}'})
                except Exception as e:
                    print(f'Error while trying to play URI: {e}')
                    return JsonResponse({'status': 'error', 'message': f'Failed to add track to queue: {e}'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Speaker not found'})
        else:
            return JsonResponse({'status': 'error', 'message': 'No Sonos speakers found'})
    
   
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def play_track(request):
    if request.method == 'POST':
        speaker_uid = request.POST.get('speaker_name')  # Get the speaker UID from the form data
        track_index = request.POST.get('track_index')  # Get the track index from the form data

        if not speaker_uid or track_index is None:
            return JsonResponse({'status': 'error', 'message': 'Invalid parameters'}, status=400)

        # Discover Sonos speakers
        speakers = soco.discover()
        if not speakers:
            return JsonResponse({'status': 'error', 'message': 'No Sonos speakers found'}, status=404)

        # Find the speaker by its UID
        speaker = next((s for s in speakers if s.uid == speaker_uid), None)
        if not speaker:
            return JsonResponse({'status': 'error', 'message': f'Speaker {speaker_uid} not found'}, status=404)

        try:
            # Play the selected track from the queue
            speaker.play_from_queue(int(track_index))
            return JsonResponse({'status': 'success', 'message': f'Playing track {track_index} on {speaker_uid}'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Failed to play track: {str(e)}'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def get_sonos_speaker_info():
    speakers_info = []
    speakers = soco.discover()
    all_ungrouped_speakers = []

    if speakers:
        for speaker in speakers:
            # Get list of speakers that are not part of any group
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
                album_art_uri = track.album_art_uri if track.album_art_uri else None
                queue_with_album_art.append({
                    'title': track.title,
                    'artist': track.creator,  # Use 'creator' for the artist
                    'album_art': album_art_uri
                })
            
            # Copy list of ungrouped speakers but remove the current speaker
            ungrouped_speakers = all_ungrouped_speakers.copy()
            try:
                ungrouped_speakers.remove(speaker)
            except ValueError:
                pass

            # Prepare the speaker info
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
            
        speakers_info = sorted(speakers_info, key=lambda x: x['name'])
    
    return speakers_info

####################################################
# Spotify Integration
####################################################

def spotify_test(request):
    return render(request, 'spotify_test.html')

def fetch_spotify_data(request):
    if request.user.is_authenticated:
        print('User is authenticated')
        try:
            social = request.user.social_auth.get(provider='spotify')
            access_token = social.extra_data['access_token']
            refresh_token = social.extra_data['refresh_token']
            
            #print key/value pairs from extra_data
            print(f'Extra data: {social.extra_data}')
            
           
            print(f'Access token: {access_token}')
            print(f'Social: {social}') 
            
            # # Check if token is expired
            # if expires_at and datetime.now(datetime.timezone.utc) > expires_at:
            #     print("Access token has expired. Attempting to refresh...")

            #     # Trigger token refresh using social-auth's backend
            #     strategy = load_strategy()
            #     backend = social.get_backend_instance(strategy)
            #     new_tokens = backend.refresh_token(refresh_token)

            #     # Update the tokens in the database
            #     social.extra_data['access_token'] = new_tokens['access_token']
            #     social.extra_data['expires_at'] = new_tokens['expires_at']
            #     social.save()
                
            #     # Update the access token to use the refreshed one
            #     access_token = new_tokens['access_token']
            #     print("Token refreshed successfully.")            

            sp = spotipy.Spotify(auth=access_token)
            
            print(f'spotify object: {sp}')

            # Fetch recently played tracks
            recently_played_results = sp.current_user_recently_played(limit=12)
            recently_played = [{
                'name': track['track']['name'],
                'artist': track['track']['artists'][0]['name'],
                'uri': track['track']['uri'],
                'album_art': track['track']['album']['images'][0]['url'] if track['track']['album']['images'] else None  # Fetch album art
            } for track in recently_played_results['items']]

            # Fetch favorite tracks
            favorite_tracks_results = sp.current_user_saved_tracks(limit=12)
            favorite_tracks = [{
                'name': track['track']['name'],
                'artist': track['track']['artists'][0]['name'],
                'uri': track['track']['uri'],
                'album_art': track['track']['album']['images'][0]['url'] if track['track']['album']['images'] else None  # Fetch album art
            } for track in favorite_tracks_results['items']]

            return JsonResponse({
                'recently_played': recently_played,
                'favorite_tracks': favorite_tracks,
            })
        except UserSocialAuth.DoesNotExist:
            return JsonResponse({'error': 'Spotify account not connected'}, status=401)
    else:
        return JsonResponse({'error': 'User not authenticated'}, status=401)



# In views.py
def spotify_search(request):
    query = request.GET.get('query')
    # Add logic to search Spotify with the query
    # Use your Spotify API integration to perform the search
    context = {
        'search_results': [],  # Replace with actual search results
    }
    return render(request, 'partials/spotify.html', context)



# def sonos_control(request):
#     # Your speaker discovery logic
#     speakers = []  # Populate this with your speaker information

#     if request.method == 'POST':
#         action = request.POST.get('action')
#         speaker_name = request.POST.get('speaker_name')

#         # Find the correct speaker using SoCo
#         speaker = get_speaker_by_name(speaker_name)
        
#         if action == 'play_spotify_uri':
#             spotify_uri = request.POST.get('spotify_uri')
#             try:
#                 # Play the Spotify URI on the Sonos speaker
#                 speaker.play_uri(spotify_uri)
#                 message = f"Playing {spotify_uri} on {speaker_name}"
#             except SoCoUPnPException as e:
#                 message = f"Error: Could not play the URI: {e}"

#             return JsonResponse({'status': 'success', 'message': message})
#         elif action == 'volume':
#             # Handle volume change logic here
#             pass
#         elif action == 'toggle_group':
#             # Handle grouping logic here
#             pass

#     return render(request, 'your_template.html', {'speaker_info': speakers})

# def get_speaker_by_name(name):
#     # Function to discover speakers and return the one matching the name
#     devices = soco.discover()
#     for device in devices:
#         if device.player_name == name:
#             return device
#     return None

# import requests

# def play_spotify_on_sonos(room_name, spotify_uri):
#     sonos_api_url = f'http://<SONOS_API_SERVER>:5005/{room_name}/spotify/{spotify_uri}'
    
#     try:
#         response = requests.get(sonos_api_url)
#         if response.status_code == 200:
#             print(f'Successfully started playing {spotify_uri} on {room_name}')
#         else:
#             print(f'Failed to play track: {response.content}')
#     except requests.RequestException as e:
#         print(f'Error calling Sonos API: {e}')


# def play_spotify_on_sonos(request):
#     if request.method == 'POST':
#         room_name = request.POST.get('room_name')
#         spotify_uri = request.POST.get('spotify_uri')
        
#         print(f'Looking for speaker: {room_name}')
        
#         # Find the Sonos speaker by name
#         speakers = soco.discover()
#         if speakers:
#             speaker = next((s for s in speakers if s.player_name == room_name), None)
#             if speaker:
#                 try:
#                     share_link = ShareLinkPlugin(speaker)
#                     # Stop any current playback first
#                     print(f'Stopping current playback on {room_name}')
#                     speaker.stop()
                    
#                     share_link.add_share_link_to_queue('https://open.spotify.com/track/5Z01UMMf7V1o0MzF86s6WJ?si=a1a95142a3e249d8')
#                     #index = share_link.add_share_link_to_queue('https://open.spotify.com/track/5bf3qVyRtIpk4Ym3JHalWk?si=af0cc1b567eb4631')
#                     #print(f'Added Spotify URI to queue at index: {index}')
#                     speaker.play_from_queue(index=1)
#                     return redirect('success')
#                 except Exception as e:
#                     print(f'Error while trying to play URI: {e}')
#                     return render(request, 'error.html', {'error': f'Failed to play URI: {e}'})
#             else:
#                 return render(request, 'error.html', {'error': 'Speaker not found'})
#         else:
#             return render(request, 'error.html', {'error': 'No Sonos speakers found'})
    
#     context = {
#         'spotify_uri': 'x-sonos-spotify:spotify%3atrack%3a5Z01UMMf7V1o0MzF86s6WJ?sid=9&flags=8224&sn=1',
#         'room_name': 'Kitchen'
#     }
    
#     return render(request, 'play_spotify.html', context)



