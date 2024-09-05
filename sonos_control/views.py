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
        # Get current track information and play state
        current_track = speaker.get_current_track_info()
        volume = speaker.volume
        album_art = current_track.get('album_art')

        # Check if album art is available, if not, use the default album art
        if not album_art or album_art == "":
            album_art = static('default_album_art.webp')

        # Get play state (playing, paused, stopped)
        play_state = speaker.get_current_transport_info().get('current_transport_state')
        # Get the list of speakers grouped with the current speaker
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
        target_speaker_name = request.POST.get('target_speaker')

        # Find the target speaker and the speaker being modified
        speaker = next(sp for sp in speakers if sp.player_name == speaker_name)
        target_speaker = next(sp for sp in speakers if sp.player_name == target_speaker_name)

        try:
            if action == 'toggle_group':
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

    # Pass all speakers to the template, including ungrouped ones
    other_speakers = [sp.player_name for sp in speakers if sp not in speaker.group.members]

    return render(request, 'sonos.html', {'speaker_info': speaker_info, 'other_speakers': other_speakers})
