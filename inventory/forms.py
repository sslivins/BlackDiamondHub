from django import forms
from .models import Item

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'description', 'desc_long', 'room', 'requires_batteries', 'battery_type', 'number_of_batteries', 'picture']
