from selenium import webdriver
from selenium.webdriver.common.by import By
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import TestCase
from django.urls import reverse
from .models import Feedback
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
import time
from datetime import timedelta
from django.utils import timezone


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


class FeedbackSeleniumTest(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        options = Options()
        options.add_argument('--headless')  # Run Chrome in headless mode
        options.add_argument('--no-sandbox')  # Bypass OS security model, necessary in some environments
        options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
        options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
        cls.browser = webdriver.Chrome(options=options)
        cls.browser.set_window_size(1920, 1080)
        
        cls.browser.implicitly_wait(10)        

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def setUp(self):
        # Create some feedback messages
        for i in range(25):
            Feedback.objects.create(name=f'User {i}', email=f'user{i}@example.com', message=f'Message {i}', page_url='/feedback/?page=1')

    def test_message_count_display(self):
        self.browser.get(self.live_server_url + reverse('view_feedback'))
        self.browser.implicitly_wait(10)  # Wait for the JavaScript to execute
        # Find the element that displays the number of messages
        message_count_element = self.browser.find_element(By.ID, 'message-count')
        # Assert that the message count is displayed correctly
        self.assertEqual(message_count_element.text, "Showing 1-20 of 25 messages")
        
    def test_message_count_live_update(self):
        #test for live updates of the message count
        self.browser.get(self.live_server_url + reverse('view_feedback'))
        
        #create a new feedback message
        Feedback.objects.create(name=f'User 25', email=f'user25@example.com', message=f'Message 25', page_url='/feedback/?page=1')
        
        # Clear the `data-refreshed` attribute before starting the test
        self.browser.execute_script("document.getElementById('feedback-table-container').removeAttribute('data-refreshed');")

        # Wait until the interval has fired and the table has been refreshed
        WebDriverWait(self.browser, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#feedback-table-container[data-refreshed='true']"))
        )
        
        message_count_element = self.browser.find_element(By.ID, 'message-count')
        
        # Assert that the message count is displayed correctly
        self.assertEqual(message_count_element.text, "Showing 1-20 of 26 messages")

    def test_modal_display(self):
        Feedback.objects.create(name=f'User 50', email=f'user50@example.com', message=f'Message 50', page_url='/feedback/?page=1')
      
        self.browser.get(self.live_server_url + reverse('view_feedback'))
        
        # Wait until the table is loaded
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#feedback-table-container tbody tr'))
        )        

        # Find the first feedback row and click it to open the modal
        first_feedback_row = self.browser.find_element(By.CSS_SELECTOR, 'tbody tr')
        first_feedback_row.click()
        
        # Wait for the modal to be visible
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, 'feedbackModal'))
        )

        # Check if the modal is displayed
        modal = self.browser.find_element(By.ID, 'feedbackModal')
        self.assertTrue(modal.is_displayed())

        #check that the various fields are being displayed correctly
        #name
        name = modal.find_element(By.ID, 'feedbackName').text
        self.assertEqual(name, 'User 50')
        
        #email
        email = modal.find_element(By.ID, 'feedbackEmail').text
        self.assertEqual(email, 'user50@example.com')
        
        #url
        url = modal.find_element(By.ID, 'feedbackPageUrl').text
        self.assertTrue(url.endswith('/feedback/?page=1'))
        
        #message
        message = modal.find_element(By.ID, 'feedbackMessage').text
        self.assertEqual(message, 'Message 50')

    def test_table_background_color(self):
        """Test that the table background color is black."""
        self.browser.get(self.live_server_url + reverse('view_feedback'))
        
        # Wait until the table is loaded
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#feedback-table-container tbody tr'))
        )
        
        # Find the table element
        table = self.browser.find_element(By.CSS_SELECTOR, '.table')
        
        # Get the background color of the table
        background_color = table.value_of_css_property('background-color')
        
        # Assert that the background color is dark grey (rgba(26, 26, 26, 1))
        self.assertEqual(background_color, 'rgba(26, 26, 26, 1)')

class FeedbackPaginationTest(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        options = Options()
        options.add_argument('--headless')  # Run Chrome in headless mode
        options.add_argument('--no-sandbox')  # Bypass OS security model, necessary in some environments
        options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
        options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
        cls.browser = webdriver.Chrome(options=options)
        cls.browser.set_window_size(1920, 1080)
        
        cls.browser.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def setUp(self):
        # Create multiple feedback entries to populate the table
        for i in range(25):
            Feedback.objects.create(
                name=f'Test User {i}',
                email=f'test{i}@example.com',
                message=f'This is test message {i}',
                submitted_at=timezone.now() - timedelta(minutes=i)
            )
            
    def test_pagination_and_refresh(self):
        # Navigate to the feedback view page
        self.browser.get(f'{self.live_server_url}/feedback/')
        
        # Wait until the table is loaded
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#feedback-table-container tbody tr'))
        )

        # Capture the initial state of the table
        initial_rows = self.browser.find_elements(By.CSS_SELECTOR, '#feedback-table-container tbody tr')
        initial_data = [row.text for row in initial_rows]

        # Clear the `data-refreshed` attribute before starting the test
        self.browser.execute_script("document.getElementById('feedback-table-container').removeAttribute('data-refreshed');")

        # Wait until the interval has fired and the table has been refreshed
        WebDriverWait(self.browser, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#feedback-table-container[data-refreshed='true']"))
        )

        # Capture the state of the table after refresh
        refreshed_rows = self.browser.find_elements(By.CSS_SELECTOR, '#feedback-table-container tbody tr')
        refreshed_data = [row.text for row in refreshed_rows]

        # Verify that the data in the table remains the same after refresh
        self.assertEqual(initial_data, refreshed_data)

    def test_pagination_order(self):
        # Navigate to the feedback view page
        self.browser.get(f'{self.live_server_url}/feedback/')
        
        # Wait until the table is loaded
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#feedback-table-container tbody tr'))
        )

        # Capture the timestamps from the table and verify they're in descending order
        rows = self.browser.find_elements(By.CSS_SELECTOR, '#feedback-table-container tbody tr')
        timestamps = [row.find_element(By.CSS_SELECTOR, 'td:nth-child(4)').text for row in rows]
        
        # Convert the timestamps to datetime objects if needed, and sort them in descending order
        # For simplicity, assume timestamps are already in a sortable format
        
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
    
    def test_refresh_after_adding_feedback(self):
        # Navigate to the feedback view page
        self.browser.get(f'{self.live_server_url}/feedback/')
        
        # Wait until the table is loaded
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#feedback-table-container tbody tr'))
        )
        
        # Add a new feedback entry
        Feedback.objects.create(
            name='New Test User',
            email='newtestuser@example.com',
            message='This is a new test message',
            submitted_at=timezone.now()
        )

        # Clear the `data-refreshed` attribute before starting the test
        self.browser.execute_script("document.getElementById('feedback-table-container').removeAttribute('data-refreshed');")

        # Wait until the interval has fired and the table has been refreshed
        WebDriverWait(self.browser, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#feedback-table-container[data-refreshed='true']"))
        )
        
        # Capture the table data after refresh
        refreshed_rows = self.browser.find_elements(By.CSS_SELECTOR, '#feedback-table-container tbody tr')
        refreshed_data = [row.text for row in refreshed_rows]

        # Verify the new feedback is in the table
        self.assertTrue(any('New Test User' in row for row in refreshed_data))
    
    def test_refresh_after_deleting_feedback(self):
        # Navigate to the feedback view page
        self.browser.get(f'{self.live_server_url}/feedback/')
        
        # Wait until the table is loaded
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#feedback-table-container tbody tr'))
        )
        
        # Delete the latest feedback entry
        latest_feedback = Feedback.objects.first()
        latest_feedback.delete()

        # Clear the `data-refreshed` attribute before starting the test
        self.browser.execute_script("document.getElementById('feedback-table-container').removeAttribute('data-refreshed');")

        # Wait until the interval has fired and the table has been refreshed
        WebDriverWait(self.browser, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#feedback-table-container[data-refreshed='true']"))
        )
        
        # Capture the table data after refresh
        refreshed_rows = self.browser.find_elements(By.CSS_SELECTOR, '#feedback-table-container tbody tr')
        refreshed_data = [row.text for row in refreshed_rows]

        # Verify the deleted feedback is no longer in the table
        self.assertFalse(any(latest_feedback.message in row for row in refreshed_data))
            
    def test_pagination_second_page_after_refresh(self):
        # Navigate to the feedback view page
        self.browser.get(f'{self.live_server_url}/feedback/')
        
        # Wait until the table is loaded
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#feedback-table-container tbody tr'))
        )
        
        #click on the next page button
        next_button = self.browser.find_element(By.CSS_SELECTOR, '.page-item.next a')
        next_button.click()
        
        #wait for the table to load
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#feedback-table-container tbody tr'))
        )

        # Capture the initial state of the table
        initial_rows = self.browser.find_elements(By.CSS_SELECTOR, '#feedback-table-container tbody tr')
        initial_data = [row.text for row in initial_rows]

        # Clear the `data-refreshed` attribute before starting the test
        self.browser.execute_script("document.getElementById('feedback-table-container').removeAttribute('data-refreshed');")

        # Wait until the interval has fired and the table has been refreshed
        WebDriverWait(self.browser, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#feedback-table-container[data-refreshed='true']"))
        )

        # Capture the state of the table after refresh
        refreshed_rows = self.browser.find_elements(By.CSS_SELECTOR, '#feedback-table-container tbody tr')
        refreshed_data = [row.text for row in refreshed_rows]
        
        # Verify that the data in the table remains the same after refresh
        self.assertEqual(initial_data, refreshed_data)