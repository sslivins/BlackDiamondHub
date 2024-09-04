from django.shortcuts import render
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
        
        print(f'Speaker: {speaker.player_name} current play state: {play_state}')

        speaker_info.append({
            'name': speaker.player_name,
            'track': current_track.get('title', 'Nothing Playing'),
            'artist': current_track.get('artist', 'Unknown Artist'),
            'album': current_track.get('album', 'Unknown Album'),
            'album_art': album_art,
            'volume': volume,
            'play_state': play_state,  # Track the play state
            'speaker': speaker
        })

    if request.method == 'POST':
        print(f'Got POST request: {request.POST}')
        speaker_name = request.POST.get('speaker_name')
        action = request.POST.get('action')
        volume = request.POST.get('volume', None)
        target_group_speaker_name = request.POST.get('target_group_speaker_name', None)

        # Find the corresponding speaker by name
        for info in speaker_info:
            if info['name'] == speaker_name:
                try:
                    # Handle play and pause actions based on current play state
                    if action == 'play' and info['play_state'] in ['STOPPED', 'PAUSED_PLAYBACK']:
                        info['speaker'].play()
                    elif action == 'pause' and info['play_state'] == 'PLAYING':
                        info['speaker'].pause()
                    elif action == 'volume' and volume:
                        info['speaker'].volume = int(volume)
                    elif action == 'join' and target_group_speaker_name:
                        # Join speaker to a group led by another speaker
                        target_speaker = next(s for s in speakers if s.player_name == target_group_speaker_name)
                        info['speaker'].join(target_speaker)
                    elif action == 'unjoin':
                        # Unjoin speaker from the group
                        info['speaker'].unjoin()
                except SoCoUPnPException as e:
                    print(f"Error controlling speaker {info['name']}: {e}")
                break

    return render(request, 'sonos.html', {'speaker_info': speaker_info})
