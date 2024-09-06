from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class SpotifyToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)  # Link tokens to a user if logged in
    guest_id = models.CharField(max_length=50, null=True, blank=True, unique=True) 
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    token_type = models.CharField(max_length=50)
    expires_in = models.IntegerField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"SpotifyToken for {self.user.username}"
        else:
            return f"SpotifyToken for guest {self.guest_id}"
    
    def is_expired(self):
        """Check if the access token has expired."""
        #expires_at is a unix timestamp so compare that to current time
        return timezone.now() > self.expires_at
