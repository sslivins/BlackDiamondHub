from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import ItemForm  # Ensure you have an ItemForm in forms.py
from .models import Item

import base64
import qrcode
import io

def index(request):
    items = Item.objects.all().order_by('id')
    return render(request, 'index.html', {'items': items})

def item_detail(request, id):
    item = get_object_or_404(Item, pk=id)
    
    # Generate QR code
    item_url = request.build_absolute_uri(reverse('item_detail', args=[id]))
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(item_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_code_data = base64.b64encode(buffer.getvalue()).decode("utf-8")    
    
    context = {
        'item': item,
        'qr_code_data': qr_code_data,  # Pass the QR code data to the template
    }
    return render(request, 'item_detail.html', context)  

@login_required
def edit_item(request, id):
    # Get the item object or return 404 if not found
    item = get_object_or_404(Item, pk=id)
    
    print(f"Editing item: {item}, request method: {request.method}")
    
    # If the request is POST, it means the form was submitted
    if request.method == 'POST':
        # Bind the form to the POST data and the current item instance
        form = ItemForm(request.POST, request.FILES, instance=item)
        
        if form.is_valid():
            # Save the form and redirect to the inventory view
            print("Form is valid. Saving...")
            form.save()
            return redirect('inventory')
        else:
            print(f"Form is invalid. Errors: {form.errors}")
    else:
        # If the request is GET, populate the form with the item data
        form = ItemForm(instance=item)
    
    # Render the edit.html template with the form and item data
    return render(request, 'edit.html', {'form': form, 'item': item})
  
def add_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('inventory')  # Redirect to the inventory page after adding the item
    else:
        form = ItemForm()
    return render(request, 'add_item.html', {'form': form})
  
  
@login_required
def profile(request):
    return render(request, 'profile.html')  