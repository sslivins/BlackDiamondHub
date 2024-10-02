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
from django.contrib.auth import logout
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
import qrcode
import io
import base64
import uuid
from django.core.cache import cache
from .utils import generate_auth_url, generate_qr_code
from .cache_handler import ServerCacheHandler

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

def sonos_clear_queue(speaker_uid):
    
    if not speaker_uid:
        return {'status': 'error', 'message': 'Invalid parameters', 'status_code': 400}    
        
    # Discover and find the speaker by UID
    speakers = soco.discover()
    speaker = next((s for s in speakers if s.uid == speaker_uid), None)

    if speaker:
        try:
            # Clear the speaker's queue
            speaker.clear_queue()
            return {'status': 'success', 'message': 'Queue cleared'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    else:
        return {'status': 'error', 'message': 'Speaker not found'}

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

def spotify_view(request):
    if request.user.is_authenticated:
        # User is authenticated; render the template as before
        return render(request, 'spotify.html')
    else:
        # Generate a unique session ID and store it
        session_id = str(uuid.uuid4())
        request.session['session_id'] = session_id

        # Generate the Spotify authorization URL with the state parameter
        auth_url = generate_auth_url(session_id)

        # Generate the QR code image
        qr_code_img = generate_qr_code(auth_url)

        # Pass the QR code image and session ID to the template
        context = {
            'qr_code_img': qr_code_img,
            'session_id': session_id,
        }
        return render(request, 'partials/spotify.html', context)
    
def spotify_auth_qrcode(request):
    # Generate a unique session ID and store it
    session_id = str(uuid.uuid4())
    
    # Generate the Spotify authorization URL with the state parameter
    auth_manager = SpotifyOAuth(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI,
        scope=settings.SPOTIFY_SCOPE,
        state=session_id,
        cache_handler=ServerCacheHandler(session_id),
    )
    auth_url = auth_manager.get_authorize_url()

    # Generate the QR code image
    qr_code_img = generate_qr_code(auth_url)

    # Return the QR code image and session ID as JSON
    response_data = {
        'qr_code_img': qr_code_img,
        'session_id': session_id,
    }

    return JsonResponse(response_data)    

def logout_and_disconnect_spotify(request):
    
    print("Logging out and disconnecting Spotify...")
    # Disconnect Spotify social account
    try:
        user_social_auth = request.user.social_auth.get(provider='spotify')
        print(f'Revoking tokens')
        user_social_auth.delete()
        
        token_info = user_social_auth.extra_data
        print(f"Revoking access token: {token_info['access_token']}")
        
    except UserSocialAuth.DoesNotExist:
        print("User does not have a Spotify social authentication.")
        pass

    # Log out the user
    logout(request)
    print(f"Token revoked: {token_info['access_token']}")
    return redirect('sonos_control')

def get_spotify_instance(user):
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope=settings.SPOTIFY_SCOPE,
        ))
    except spotipy.exceptions.SpotifyException as e:
        print(f"Error: {e}")
        
    return sp

def spotify_login(request):
    # This will redirect to Spotify if the token is invalid or missing
    sp = get_spotify_instance(request)
    if isinstance(sp, spotipy.Spotify):
        # Already authenticated
        return redirect('spotify_home')
    else:
        # Redirected to Spotify's auth page
        return sp

def spotify_auth_status(request):
    session_id = request.GET.get('session_id')

    cache_handler = ServerCacheHandler(session_id)
    token_info = cache_handler.get_cached_token()
    
    #print(f"Session ID: {session_id}, Token Info: {token_info}")

    if token_info:
        #print("Token info found in cache")
        # Tokens are available, user is authenticated
        return JsonResponse({'authorized': True})
    else:
        return JsonResponse({'authorized': False})
 
def spotify_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')

    cache_handler = ServerCacheHandler(state)
    auth_manager = SpotifyOAuth(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI,
        state=state,
        cache_handler=cache_handler
    )


    try:
        # Exchange the code for access token, token_info is saved in the cache
        token_info = auth_manager.get_access_token(code)
        #print(f"Token info: {token_info}")
    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    # Token info is automatically saved in the session via cache_handler

    return JsonResponse({'Success': True})

    
def spotify_home(request):
    sp = get_spotify_instance(request)
    if isinstance(sp, spotipy.Spotify):
        # Fetch user data or playlists
        user_profile = sp.current_user()
        return render(request, 'spotify.html', {'user_profile': user_profile})
    else:
        # Redirect to login if not authenticated
        return sp    

def get_spotify_instance_old(user):

    social = user.social_auth.get(provider='spotify')
    token_info = social.extra_data
    
    try:
        # Create Spotipy instance with current access token
        sp = spotipy.Spotify(auth=token_info['access_token'])

        # Make a test API call to check if the token is valid
        sp.current_user()  # This will throw an exception if the token has expired

    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 401:  # 401 Unauthorized, meaning the token has expired
            print("Token expired, refreshing...")
            
            # Trigger token refresh using social-auth's backend
            strategy = load_strategy()
            backend = social.get_backend_instance(strategy)
            new_tokens = backend.refresh_token(token_info['refresh_token'])

            # Update the tokens in the database
            social.extra_data['access_token'] = new_tokens['access_token']
            social.save()            
            
            # Recreate the Spotipy instance with the new token
            sp = spotipy.Spotify(auth=token_info['access_token'])

        else:
            print("Error: ", e)
            raise e  # Rethrow the exception if it's not related to token expiration

    return sp

def fetch_spotify_data(request):
    if request.user.is_authenticated:
        try:
            sp = get_spotify_instance(request.user)
            
            # Fetch recently played tracks
            recently_played_results = sp.current_user_recently_played(limit=12)
            recently_played = [{
                'name': track['track']['name'],
                'artist': track['track']['artists'][0]['name'],
                'album': track['track']['album']['name'],
                'uri': track['track']['uri'],
                'album_art': track['track']['album']['images'][0]['url'] if track['track']['album']['images'] else None  # Fetch album art
            } for track in recently_played_results['items']]

            # Fetch favorite tracks
            favorite_tracks_results = sp.current_user_saved_tracks(limit=12)
            favorite_tracks = [{
                'name': track['track']['name'],
                'artist': track['track']['artists'][0]['name'],
                'album': track['track']['album']['name'],
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

def spotify_search(request):
    query = request.GET.get('query', '')
    search_results = []

    try:
        # Get the Spotify instance for the authenticated user
        sp = get_spotify_instance(request.user)

        if query:
            # Search on Spotify for tracks, albums, and artists
            results = sp.search(q=query, type='track,album,artist', limit=18)
            
            # Structure the search results to return relevant information as JSON
            for item in results.get('tracks', {}).get('items', []):
                search_results.append({
                    'name': item['name'],
                    'artist': item['artists'][0]['name'],
                    'album': item['album']['name'],
                    'album_art': item['album']['images'][0]['url'] if item['album']['images'] else None,
                    'uri': item['uri'],
                })

    except Exception as e:
        # Catch any errors, return the error message in the JSON response
        return JsonResponse({'error': str(e)}, status=500)

    # Return the search results as JSON
    return JsonResponse({'search_results': search_results})




