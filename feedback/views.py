# feedback/views.py
import json
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dateparse import parse_datetime
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

def get_unread_feedback_count(request):
    if request.user.is_authenticated and request.user.is_staff:
        count = Feedback.objects.filter(is_read=False).count()
    else:
        count = 0
    return JsonResponse({'unread_feedback_count': count})

def view_feedback(request):
    if not request.user.is_staff:
        return redirect('landing_page')

    feedbacks = Feedback.objects.all().order_by('-submitted_at')
    paginator = Paginator(feedbacks, 20)  # Show 20 feedbacks per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'view_feedback.html', {'feedbacks': page_obj})

def fetch_new_feedback(request, last_update):
    if request.user.is_authenticated and request.user.is_staff:
        last_update_dt = parse_datetime(last_update)
        new_feedbacks = Feedback.objects.filter(submitted_at__gt=last_update_dt, is_read=False).order_by('submitted_at')
        feedback_data = []
        for feedback in new_feedbacks:
            feedback_data.append({
                'id': feedback.id,
                'name': feedback.name,
                'submitted_at': feedback.submitted_at.isoformat(),
                'is_read': feedback.is_read,
                'email': feedback.email,
                'page_url': feedback.page_url,
                'message': feedback.message,
            })
        return JsonResponse({'feedbacks': feedback_data})
    return JsonResponse({'feedbacks': []})

def mark_as_read(request, feedback_id):
    feedback = get_object_or_404(Feedback, id=feedback_id)
    feedback.is_read = True
    feedback.save()
    return redirect('view_feedback')
  
def delete_feedback(request, feedback_id):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            feedback = Feedback.objects.get(id=feedback_id)
            feedback.delete()
            return JsonResponse({'success': True})
        except Feedback.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Feedback not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

def bulk_feedback_action(request):
    if request.method == 'POST':
        # Parse the JSON body of the request
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

        feedback_ids = data.get('feedback_ids', [])
        action = data.get('action')

        if not feedback_ids or not action:
            return JsonResponse({'success': False, 'error': 'Missing data'}, status=400)

        print(f'{action} Feedback IDs: {feedback_ids}')

        if action == 'delete':
            Feedback.objects.filter(id__in=feedback_ids).delete()
        elif action == 'mark_read':
            Feedback.objects.filter(id__in=feedback_ids).update(is_read=True)
        elif action == 'mark_unread':
            Feedback.objects.filter(id__in=feedback_ids).update(is_read=False)
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)

        return JsonResponse({'success': True})

    return redirect('view_feedback')