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
    
    context = {
        'feedbacks': page_obj,
        'total_feedback_count': Feedback.objects.count()
    }
    
    return render(request, 'view_feedback.html', context)

def fetch_new_feedback(request, last_update):
    if request.user.is_authenticated and request.user.is_staff:
        last_update_dt = parse_datetime(last_update)
        limit = int(request.GET.get('limit', 20))  # Default limit to 20 if not provided
        feedback_list = Feedback.objects.filter(submitted_at__gt=last_update_dt).order_by('-submitted_at')
        total_feedback_count = Feedback.objects.count()

        feedback_data = [
            {
                'id': feedback.id,
                'name': feedback.name,
                'submitted_at': feedback.submitted_at.isoformat(),
                'is_read': feedback.is_read,
                'email': feedback.email,
                'page_url': feedback.page_url,
                'message': feedback.message,
            }
            for feedback in feedback_list[:limit]
        ]
        
        print(f'feedback_data: {feedback_data}')
        
        return JsonResponse({
            'feedbacks': feedback_data,
            'total_feedback_count': total_feedback_count
        })
    return JsonResponse({'feedbacks': [], 'total_count': 0})

def fetch_additional_feedback(request, current_count, items_to_fetch):
    """
    Fetch additional feedback messages when the number of displayed items is less than maxItemsPerPage.
    :param current_count: The number of feedback items currently displayed.
    :param items_to_fetch: The number of additional items needed to reach the maxItemsPerPage limit.
    :return: JSON response with additional feedback messages.
    """
    # Get feedback messages ordered by submission date, skipping the already displayed items
    feedbacks = Feedback.objects.all().order_by('-submitted_at')[current_count:current_count + items_to_fetch]

    # Convert the feedback queryset to a list of dictionaries
    feedback_list = list(feedbacks.values(
        'id', 'submitted_at', 'name', 'email', 'page_url', 'message', 'is_read'
    ))

    return JsonResponse({'feedbacks': feedback_list})

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