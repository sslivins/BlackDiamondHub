from .models import Feedback

def unread_feedback_count(request):
    if request.user.is_authenticated and request.user.is_staff:
        count = Feedback.objects.filter(is_read=False).count()
    else:
        count = 0
    return {
        'unread_feedback_count': count
    }
