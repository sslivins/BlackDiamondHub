# context_processors.py

def spotify_token(request):
    token_info = request.session.get('spotify_token_info')

    return {
        'has_spotify_token': token_info is not None
    }
