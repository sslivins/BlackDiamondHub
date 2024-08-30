# feedback/views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import Feedback
from django.http import JsonResponse

def submit_feedback(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        page_url = request.POST.get('page_url', '')
        
        Feedback.objects.create(name=name, email=email, page_url=page_url, message=message)
        return JsonResponse({'success': True})  # Return a JSON response indicating success

    return JsonResponse({'success': False})  # Return a JSON response indicating failure

def view_feedback(request):
    if not request.user.is_staff:
        return redirect('landing_page')

    feedbacks = Feedback.objects.all().order_by('-submitted_at')
        
    return render(request, 'view_feedback.html', {'feedbacks': feedbacks})

def mark_as_read(request, feedback_id):
    feedback = get_object_or_404(Feedback, id=feedback_id)
    feedback.is_read = True
    feedback.save()
    return redirect('view_feedback')