from django.shortcuts import render, redirect
from django.http import JsonResponse
import soco
from django.templatetags.static import static
from soco.exceptions import SoCoUPnPException

def sonos_control_view(request):
    # Discover all Sonos speakers
    speakers = list(soco.discover())

    if not speakers:
        return render(request, 'no_speakers.html')

    speaker_info = []
    for speaker in speakers:
        current_track = speaker.get_current_track_info()
        volume = speaker.volume
        album_art = current_track.get('album_art')

        if not album_art or album_art == "":
            album_art = static('default_album_art.webp')

        play_state = speaker.get_current_transport_info().get('current_transport_state')
        group = [sp.player_name for sp in speaker.group.members if sp != speaker]

        speaker_info.append({
            'name': speaker.player_name,
            'track': current_track.get('title', 'Nothing Playing'),
            'artist': current_track.get('artist', 'Unknown Artist'),
            'album': current_track.get('album', 'Unknown Album'),
            'album_art': album_art,
            'volume': volume,
            'play_state': play_state,
            'group': group,
            'speaker': speaker
        })

    speaker_info = sorted(speaker_info, key=lambda x: x['name'])

    if request.method == 'POST':
        speaker_name = request.POST.get('speaker_name')
        action = request.POST.get('action')
        target_speaker_name = request.POST.get('target_speaker_name', speaker_name)
        
        print(f'Speaker: {speaker_name}, Action: {action}, Target Speaker: {target_speaker_name}')

        speaker = next(sp for sp in speakers if sp.player_name == speaker_name)

        try:
            if action == 'play_spotify_uri':
                spotify_uri = request.POST.get('spotify_uri')
                if spotify_uri:
                    # Define the metadata for Spotify content
                    meta_template = (
                        '<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/" '
                        'xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" '
                        'xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/">'
                        '<item id="1004206cspotify%3a%2f%2f{uri}" parentID="0" restricted="true">'
                        '<dc:title>{title}</dc:title>'
                        '<upnp:class>object.item.audioItem.musicTrack</upnp:class>'
                        '<desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0">'
                        'SA_RINCON2311_X_#Svc2311-0-Token</desc></item></DIDL-Lite>'
                    )

                    # Metadata should contain the correct Spotify URI format
                    spotify_uri_encoded = spotify_uri.replace(':', '%3a')
                    metadata = meta_template.format(uri=spotify_uri_encoded, title="Spotify Track")

                    # Play Spotify URI on the selected speaker with metadata
                    speaker.play_uri(spotify_uri, meta=metadata)
                    return JsonResponse({'status': 'success', 'message': f"Playing Spotify URI on {speaker_name}"}, status=200)
                else:
                    return JsonResponse({'error': 'No Spotify URI provided'}, status=400)
            elif action == 'toggle_group':
                target_speaker = next(sp for sp in speakers if sp.player_name == target_speaker_name)
                if target_speaker in speaker.group.members:
                    target_speaker.unjoin()  # Remove from group
                else:
                    target_speaker.join(speaker)  # Add to group
            elif action == 'volume':
                volume = int(request.POST.get('volume'))
                speaker.volume = volume
                return JsonResponse({'status': 'success', 'volume': volume}, status=200)
            elif action in ['play', 'pause']:
                if action == 'play':
                    speaker.play()
                else:
                    speaker.pause()

            return JsonResponse({'status': 'success'}, status=200)

        except SoCoUPnPException as e:
            return JsonResponse({'error': str(e)}, status=400)

    other_speakers = [sp.player_name for sp in speakers if sp not in speaker.group.members]

    return render(request, 'sonos.html', {'speaker_info': speaker_info, 'other_speakers': other_speakers})


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
