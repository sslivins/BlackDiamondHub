from django.db import models

class Item(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    desc_long = models.TextField(null=True, blank=True)
    room = models.CharField(max_length=255)
    requires_batteries = models.BooleanField(default=False)
    battery_type = models.CharField(max_length=50, null=True, blank=True)
    number_of_batteries = models.IntegerField(null=True, blank=True)
    picture = models.ImageField(upload_to='items/', null=True, blank=True)

    def __str__(self):
        return self.name
