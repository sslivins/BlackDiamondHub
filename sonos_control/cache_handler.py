# cache_handler.py

from spotipy.cache_handler import CacheHandler
from django.core.cache import cache

class ServerCacheHandler(CacheHandler):
    def __init__(self, state):
        self.state = state  # Use state (session ID) as the key

    def get_cached_token(self):
        return cache.get(self.state)

    def save_token_to_cache(self, token_info):
        #print(f"Saving token {token_info} to cache with key {self.state}")
        cache.set(self.state, token_info, timeout=3600)  # Tokens expire after an hour
        
