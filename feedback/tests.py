from django.test import TestCase
from django.urls import reverse
from .models import Feedback

class FeedbackViewTests(TestCase):
    def setUp(self):
        # Create some sample feedback messages
        self.feedback1 = Feedback.objects.create(name='User1', email='user1@example.com', message='Test message 1', is_read=False)
        self.feedback2 = Feedback.objects.create(name='User2', email='user2@example.com', message='Test message 2', is_read=True)

    def test_feedback_page_loads(self):
        """Test that the feedback page loads correctly."""
        response = self.client.get(reverse('view_feedback'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Feedback Messages")
        self.assertContains(response, self.feedback1.name)
        self.assertContains(response, self.feedback2.name)

    def test_no_messages(self):
        """Test that the page shows 'No messages' when there are no feedbacks."""
        Feedback.objects.all().delete()
        response = self.client.get(reverse('view_feedback'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No messages")

    def test_pagination(self):
        """Test that pagination works and shows correct number of items per page."""
        
        """remove any existing messages"""
        Feedback.objects.all().delete()
        response = self.client.get(reverse('view_feedback'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No messages")        
        
        # Create additional feedback messages
        for i in range(30):
            Feedback.objects.create(name=f'User{i+3}', email=f'user{i+3}@example.com', message=f'Test message {i+3}', is_read=False)

        response = self.client.get(reverse('view_feedback'))
        self.assertEqual(response.status_code, 200)

        # Verify that 20 items are on the first page
        table = response.context['table']
        self.assertEqual(len(table.page), 20)
        
        # Check if the pagination information is correct
        paginator = table.paginator
        self.assertEqual(paginator.num_pages, 2)  # There should be 2 pages
        self.assertEqual(table.page.number, 1)  # We should be on the first page

        # Now request the second page
        response = self.client.get(reverse('view_feedback') + '?page=2')
        self.assertEqual(response.status_code, 200)
        
        table = response.context['table']
        self.assertEqual(len(table.page), 10)  # There should be 10 items on the second page
        
        paginator = table.paginator
        self.assertEqual(paginator.num_pages, 2)  # Still 2 pages
        self.assertEqual(table.page.number, 2)  # Now we should be on the second page

    def test_bulk_delete(self):
        """Test bulk delete action."""
        response = self.client.post(reverse('bulk_feedback_action'), {
            'feedback_ids': [self.feedback1.id, self.feedback2.id],
            'action': 'delete'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_mark_read(self):
        """Test bulk mark as read action."""
        response = self.client.post(reverse('bulk_feedback_action'), {
            'feedback_ids': [self.feedback1.id],
            'action': 'mark_read'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.feedback1.refresh_from_db()
        self.assertTrue(self.feedback1.is_read)
        
    def test_mark_unread(self):
        """Test bulk mark as unread action."""
        response = self.client.post(reverse('bulk_feedback_action'), {
            'feedback_ids': [self.feedback2.id],
            'action': 'mark_unread'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.feedback2.refresh_from_db()
        self.assertFalse(self.feedback2.is_read)

    def test_modal_data(self):
        """Test that modal opens with correct feedback data."""
        response = self.client.get(reverse('view_feedback'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.feedback1.message)
        self.assertContains(response, self.feedback2.message)

        # Simulate clicking on a feedback message (would typically involve JS testing)
        feedback_row = self.feedback1
        self.assertEqual(feedback_row.name, 'User1')
        self.assertEqual(feedback_row.message, 'Test message 1')

