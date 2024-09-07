from django.shortcuts import render, redirect
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
import qrcode
from django.http import HttpResponse
import io
from django.contrib.auth.models import User
from django.http import JsonResponse
import uuid
from .models import SpotifyToken
from datetime import datetime, timezone as tz
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

def spotify_landing(request):
    # Check if the user is authenticated
    if request.user.is_authenticated:
      if SpotifyToken.objects.get(user=request.user):
        return render(request, 'spotify/spotify.html')  # Render Spotify dashboard
    else:
      if SpotifyToken.objects.get(guest_id=request.user):
        return render(request, 'spotify/spotify.html')  # Render Spotify dashboard
      
    # If not authenticated, redirect to landing page
    return render(request, 'spotify/landing.html')
  
def webplayer_view(request):
    return render(request, 'spotify/webplayer.html')  

def spotify_login(request):
    # Check if the user is logging in via the web or the QR code
    login_type = request.GET.get('type', 'web')  # 'web' or 'qr'

    if login_type == 'qr':
        # For QR code login, set the redirect URI for the QR callback
        redirect_uri = settings.SPOTIFY_REDIRECT_URI + 'qr_callback/'
    else:
        # For regular web login, use the regular callback URI
        redirect_uri = settings.SPOTIFY_REDIRECT_URI + 'callback/'

    sp_oauth = SpotifyOAuth(client_id=settings.SPOTIFY_CLIENT_ID,
                            client_secret=settings.SPOTIFY_CLIENT_SECRET,
                            redirect_uri=redirect_uri,
                            scope="user-library-read, \
                                user-read-recently-played, \
                                user-read-playback-state, \
                                user-modify-playback-state, \
                                user-read-currently-playing, \
                                streaming")
    
    print(f'Redirect URI: {redirect_uri}')

    auth_url = sp_oauth.get_authorize_url()

    if login_type == 'qr':
        # If this is a QR login, generate and return the QR code for the auth URL
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(auth_url)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')

        # Convert the image to byte array to be displayed in the template
        byte_io = io.BytesIO()
        img.save(byte_io, 'PNG')
        byte_io.seek(0)

        # Return the QR code image
        return HttpResponse(byte_io.getvalue(), content_type='image/png')
    else:
        # If this is a web login, redirect the user to the Spotify auth page
        return redirect(auth_url)

def spotify_callback(request):
    sp_oauth = SpotifyOAuth(client_id=settings.SPOTIFY_CLIENT_ID,
                            client_secret=settings.SPOTIFY_CLIENT_SECRET,
                            redirect_uri=settings.SPOTIFY_REDIRECT_URI)

    code = request.GET.get('code')
    token_info = sp_oauth.get_access_token(code)
    
    print(f"Token info: {token_info}") 

    if request.user.is_authenticated:
        # Store token for logged-in user
        spotify_token, created = SpotifyToken.objects.get_or_create(user=request.user)
    else:
        # For guest login, create or get token by guest_id
        guest_id = request.session.get('guest_id')
        if not guest_id:
            guest_id = str(uuid.uuid4())  # Generate new guest_id if not present
            request.session['guest_id'] = guest_id
        
        spotify_token, created = SpotifyToken.objects.get_or_create(guest_id=guest_id)

    # Update token details
    spotify_token.access_token = token_info['access_token']
    spotify_token.refresh_token = token_info['refresh_token']
    spotify_token.token_type = token_info['token_type']
    spotify_token.expires_in = token_info['expires_in']
    spotify_token.created_at = timezone.now()
    spotify_token.save()

    return redirect('spotify:webplayer')

def spotify_qr_callback(request):
    sp_oauth = SpotifyOAuth(client_id=settings.SPOTIFY_CLIENT_ID,
                            client_secret=settings.SPOTIFY_CLIENT_SECRET,
                            redirect_uri=settings.SPOTIFY_REDIRECT_URI + 'qr_callback/')

    code = request.GET.get('code')
    token_info = sp_oauth.get_access_token(code)
    
    print(f"Token info: {token_info}")     
    
    created = False
    
    if request.user.is_authenticated:
        spotify_token, created = SpotifyToken.objects.get_or_create(
          user=request.user,
          defaults={
            'access_token': token_info['access_token'],
            'refresh_token': token_info['refresh_token'],
            'token_type': token_info['token_type'],
            'expires_in': token_info['expires_in'],
            'expires_at': datetime.fromtimestamp(token_info['expires_at'], tz=tz.utc),
            'created_at': timezone.now(),
          }
        )
    else:
        spotify_token, created = SpotifyToken.objects.get_or_create(
          guest_id=request.user,
          defaults={
            'access_token': token_info['access_token'],
            'refresh_token': token_info['refresh_token'],
            'token_type': token_info['token_type'],
            'expires_in': token_info['expires_in'],
            'expires_at': datetime.fromtimestamp(token_info['expires_at'], tz=tz.utc),
            'created_at': timezone.now(),
          }
        )
        
    print(f"the token will expire at: {datetime.fromtimestamp(token_info['expires_at'], tz=tz.utc)}")
        
    if not created:
      spotify_token.access_token = token_info['access_token']
      spotify_token.refresh_token = token_info['refresh_token']
      spotify_token.token_type = token_info['token_type']
      spotify_token.expires_in = token_info['expires_in']
      spotify_token.expires_at = datetime.fromtimestamp(token_info['expires_at'], tz=tz.utc)
      spotify_token.created_at = timezone.now()
      print(f"Token updated")
      spotify_token.save()

    # Notify the user on the phone that they are signed in
    return render(request, 'spotify/qr_signed_in.html')
  
def check_auth(request):
  
    if request.user.is_authenticated:
      if SpotifyToken.objects.get(user=request.user).exists():
          return JsonResponse({'signed_in': True})
    else:
      # Check if the guest has a token
      if SpotifyToken.objects.get(guest_id=request.user).exists():
          return JsonResponse({'signed_in': True})

    return JsonResponse({'signed_in': False}) 

def get_spotify_client(request):
    
    access_token = get_spotify_token(request)
      
    return Spotify(auth=access_token)
  
def get_spotify_token(request):
    if request.user.is_authenticated:
      spotify_token = SpotifyToken.objects.get(user=request.user)
    else:
      spotify_token = SpotifyToken.objects.get(guest_id=request.user)
      
    print(f"Token info: {spotify_token}, current time: {timezone.now()}, token will expire at: {timezone.localtime(spotify_token.expires_at)}")
      
    #check if token is expired
    if spotify_token.is_expired():
        
        print('Token expired, refreshing...')
        
        sp_oauth = SpotifyOAuth(client_id=settings.SPOTIFY_CLIENT_ID,
                                client_secret=settings.SPOTIFY_CLIENT_SECRET,
                                redirect_uri=settings.SPOTIFY_REDIRECT_URI)
        token_info = sp_oauth.refresh_access_token(spotify_token.refresh_token)
        
        spotify_token.access_token = token_info['access_token']
        spotify_token.refresh_token = token_info['refresh_token']
        spotify_token.expires_at = datetime.fromtimestamp(token_info['expires_at'], tz=tz.utc)        
        spotify_token.created_at = timezone.now()
        spotify_token.save()
      
    return spotify_token.access_token
  

def spotify_get_token(request):
    # Get the access token (refresh it if necessary)
    access_token = get_spotify_token(request)
    
    return JsonResponse({'access_token': access_token})  # Return the access token

def spotify_search(request):
    query = request.GET.get('q')
    
    if query:
        sp = get_spotify_client(request)
        try:
          results = sp.search(q=query, type='track', limit=10)
        except Exception as e:
          print(f'Error searching Spotify: {e}')
          return JsonResponse({"error": str(e)}, status=500)

        return JsonResponse(results, safe=False)
    
    return JsonResponse({"error": "No query provided"}, status=400)
  
@csrf_exempt
def spotify_play(request):
    track_uri = request.GET.get('track_uri')
    device_id = request.GET.get('device_id')

    if not track_uri or not device_id:
        return JsonResponse({'error': 'Track URI or Device ID missing'}, status=400)

    sp = get_spotify_client(request)
    try:
        sp.start_playback(device_id=device_id, uris=[track_uri])
        return JsonResponse({'message': f'Playing track {track_uri} on device {device_id}'})
    except Spotify.SpotifyException as e:
        return JsonResponse({'error': str(e)}, status=500)

def spotify_recently_played(request):
    sp = get_spotify_client(request)
    results = sp.current_user_recently_played(limit=10)
    return JsonResponse(results, safe=False)
  
def spotify_favorites(request):
    try:
      sp = get_spotify_client(request)
    except Exception as e:
      print(f'Error searching Spotify: {e}')
      return JsonResponse({"error": str(e)}, status=500)

    results = sp.current_user_saved_tracks(limit=10)
    
    return JsonResponse(results, safe=False)
  
def spotify_devices(request):
    sp = get_spotify_client(request)  # Get the authenticated Spotify client
    try:
        devices = sp.devices()  # Fetch all available devices
        print(f"Devices: {devices}")
        return JsonResponse(devices)  # Return the list of devices (including Sonos speakers if connected)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Transfer playback to a specific device
@csrf_exempt  # You can exempt CSRF for this request if needed
def spotify_transfer_playback(request):
    device_id = request.GET.get('device_id')
    if not device_id:
        return JsonResponse({'error': 'Device ID not provided'}, status=400)

    sp = get_spotify_client(request)
    try:
        sp.transfer_playback(device_id)
        return JsonResponse({'message': f'Transferred playback to device {device_id}'})
    except Spotify.SpotifyException as e:
        return JsonResponse({'error': str(e)}, status=500)
  
def get_active_devices(spotify_client):
    devices = spotify_client.devices()
    return devices['devices']
  
# Set the active device for playback
def set_active_device(spotify_client, device_id):
  
    try:
      spotify_client.transfer_playback(device_id)
    except Spotify.SpotifyException as e:
      print(f'Error setting active device: {e}')
      return False
    
    return True
  
def check_devices(spotify_client):
    devices = spotify_client.devices()
    for device in devices['devices']:
        print(f"Device: {device['name']}, Active: {device['is_active']}, Restricted: {device['is_restricted']}")
        if not device['is_restricted']:
            return device['id']  # Return the first unrestricted device
    return None
  
def play_on_active_device(spotify_client, track_uri):
    # Fetch active devices
    devices = spotify_client.devices()

    # Find an active, unrestricted device
    active_device = None
    for device in devices['devices']:
        if device['is_active'] and not device['is_restricted']:
            active_device = device['id']
            break

    if not active_device:
        return {'error': 'No active, unrestricted devices available.'}

    # Play the track on the active device
    spotify_client.start_playback(device_id=active_device, uris=[track_uri])
    return {'message': f'Playing {track_uri} on {active_device}'}