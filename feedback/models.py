from django.db import models

class Feedback(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    page_url = models.URLField(max_length=200, blank=True)

    def __str__(self):
        return f"Feedback from {self.name or 'Anonymous'}"
