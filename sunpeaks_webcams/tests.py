from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import LiveServerTestCase
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import unittest

import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs, urlsplit
import re

from django.test import TestCase
from dateutil import parser as dt_parser
import pytz

from sunpeaks_webcams.views import check_for_new_webcams

class CheckForNewWebcamsTests(TestCase):
    def test_check_for_new_webcams_data(self):
        webcams = check_for_new_webcams()
        
        # Verify that we got at least one webcam entry.
        expected_cams = 7
        self.assertTrue(len(webcams) >= expected_cams, f"Expected at {expected_cams} webcams, got {len(webcams)}")
        
        # Define expected static values keyed by camera_name.
        # Only the static parts are expected to remain constant.
        expected = {
            'Sundance': {
                'static_image_url': 'https://www.sunpeaksresort.com/sites/default/files/spr_website_data/webcams/sundance.jpg',
                'location': 'Top of Sundance Express Chairlift',
                'elevation': "1,731m (5,677')"
            },
            'Valley': {
                'static_image_url': 'https://www.sunpeaksresort.com/sites/default/files/spr_website_data/webcams/Valley.jpg',
                'location': 'Village Square',
                'elevation': "Village Base, 1,255m (4,116')"
            },
            'View of Top of the World': {
                'static_image_url': 'https://www.sunpeaksresort.com/sites/default/files/spr_website_data/webcams/westbowl-totw.jpg',
                'location': 'Top of West Bowl',
                'elevation': "2,093m (6,867')"
            },
            'West Bowl Express': {
                'static_image_url': 'https://www.sunpeaksresort.com/sites/default/files/spr_website_data/webcams/westbowl.jpg',
                'location': 'Top of West Bowl',
                'elevation': "2,093m (6,867')"
            },
            'Mt. Tod, View from Mt. Morrisey': {
                'static_image_url': 'https://www.sunpeaksresort.com/sites/default/files/spr_website_data/webcams/view of mt todd.jpg',
                'location': 'Top of Morrisey Express',
                'elevation': "1,672m (5,495')"
            },
            'Elevation': {
                'static_image_url': 'https://www.sunpeaksresort.com/sites/default/files/spr_website_data/webcams/ele_view_of_morrisey.jpg',
                'location': 'Base of the Elevation Chairlift',
                'elevation': "1,600m (5,249')"
            },
            'Orient Quad Base': {
                'static_image_url': 'https://www.sunpeaksresort.com/sites/default/files/spr_website_data/webcams/Orient.jpg',
                'location': 'Base of the Orient Quad',
                'elevation': "1,284m (4,213')"
            },
            'Village Day Lodge Slopeside': {
                'static_image_url': 'https://www.sunpeaksresort.com/sites/default/files/spr_website_data/webcams/Village Day Lodge Slopeside.jpg',
                'location': 'Village Day Lodge',
                'elevation': "Village Base, 1,255m (4,116')"
            },
            'Base of OSV': {
                'static_image_url': 'https://www.sunpeaksresort.com/sites/default/files/spr_website_data/webcams/ele_view_of_OSV.jpg',
                'location': 'Base of the Elevation Chairlift',
                'elevation': "1,600m (5,249')"
            },
            'Sundance Lift Base': {
                'static_image_url': 'https://www.sunpeaksresort.com/sites/default/files/spr_website_data/webcams/Sundance Lift Base.jpg',
                'location': 'Village Square',
                'elevation': "Village Base, 1,255m (4,116')"
            },
        }
        
        
        # Get current UTC time and the current Pacific Time via pytz.
        now_utc = datetime.now(timezone.utc)
        pacific = pytz.timezone('America/Los_Angeles')
        now_pacific = datetime.now(pacific)

        for webcam in webcams:
            # Expected fields in each webcam entry.
            for field in ['camera_name', 'image_url', 'timestamp', 'last_updated', 'location', 'elevation']:
                self.assertIn(field, webcam, f"Expected key '{field}' missing in webcam data.")

            camera_name = webcam['camera_name']
            self.assertIn(camera_name, expected, f"Unexpected camera_name: {camera_name}")
            exp = expected[camera_name]
            
            # Verify the image_url static part (before '?timestamp=') remains constant.
            image_url = webcam['image_url']
            split_parts = image_url.split('?timestamp=')
            self.assertGreater(len(split_parts), 1, f"image_url does not contain '?timestamp=': {image_url}")
            static_url = split_parts[0]
            self.assertEqual(static_url, exp['static_image_url'],
                             f"For camera '{camera_name}', expected static image URL '{exp['static_image_url']}', got '{static_url}'")
            
            # Extract and verify the timestamp from URL.
            ts_str = split_parts[1]
            try:
                ts_int = int(ts_str)
            except ValueError:
                self.fail(f"Timestamp '{ts_str}' in image_url for '{camera_name}' is not a valid integer")
            # Verify the timestamp is not more than one hour old.
            current_unix = int(time.time())
            self.assertLessEqual(
                current_unix - ts_int, 15*60,
                f"Timestamp {ts_int} for '{camera_name}' is older than one hour."
            )
            
            # Verify last_updated occurred within the last hour.
            # Remove possible ordinal suffixes from the day like 'th', 'st', etc.
            last_updated_text = webcam['last_updated']
            cleaned_text = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', last_updated_text)
            try:
                # Use dateutil to parse. Assume the string is for the current day and in Pacific time.
                parsed_last_updated = dt_parser.parse(cleaned_text, fuzzy=True)
                # Because the returned string may not include a year, set the year to current.
                parsed_last_updated = parsed_last_updated.replace(year=now_pacific.year)
            except Exception as e:
                self.fail(f"Could not parse last_updated '{last_updated_text}' for '{camera_name}': {e}")
            
            # Compute the difference in minutes.
            delta = now_pacific - pacific.localize(parsed_last_updated)
            self.assertLessEqual(delta, timedelta(minutes=15),
                f"Last updated for '{camera_name}' is more than an hour old: {parsed_last_updated} (delta: {delta})")
            
            # Verify expected values for location and elevation.
            self.assertEqual(
                webcam['location'], exp['location'],
                f"For camera '{camera_name}', expected location: '{exp['location']}', but got '{webcam['location']}'"
            )
            self.assertEqual(
                webcam['elevation'], exp['elevation'],
                f"For camera '{camera_name}', expected elevation: '{exp['elevation']}', but got: '{webcam['elevation']}'"
            )

class SunPeaksWebcamsTest(StaticLiveServerTestCase):
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

    def test_background_color(self):
        self.browser.get(f'{self.live_server_url}/sunpeaks_webcams/')
        body = self.browser.find_element(By.TAG_NAME, 'body')
        background_color = body.value_of_css_property('background-color')
        self.assertEqual(background_color, 'rgba(0, 0, 0, 1)')

    def test_images_are_displayed(self):
        self.browser.get(f'{self.live_server_url}/sunpeaks_webcams/')
        images = self.browser.find_elements(By.CSS_SELECTOR, '#webcams img')
        self.assertTrue(len(images) > 0, "No images found on the page")

    def test_image_modal_opens(self):
        self.browser.get(f'{self.live_server_url}/sunpeaks_webcams/')
        first_image = self.browser.find_element(By.CSS_SELECTOR, '#webcams img')
        first_image.click()

        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, 'webcam-image-modal-image'))
        )

        modal = self.browser.find_element(By.ID, 'webcam-image-modal-image')
        self.assertTrue(modal.is_displayed(), "Modal did not open when the image was clicked")

    def test_modal_closes(self):
        self.browser.get(f'{self.live_server_url}/sunpeaks_webcams/')
        first_image = self.browser.find_element(By.CSS_SELECTOR, '#webcams img')
        first_image.click()

        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, 'webcam-image-modal-image'))
        )

        close_button = self.browser.find_element(By.CSS_SELECTOR, '#webcam-image-modal .close')
        close_button.click()

        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element((By.ID, 'webcam-image-modal-image'))
        )

        modal = self.browser.find_element(By.ID, 'webcam-image-modal-image')
        self.assertFalse(modal.is_displayed(), "Modal did not close when the close button was clicked")

class FeedbackModalTest(LiveServerTestCase):
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

    def test_feedback_modal_submission(self):
        
        #get snapshot of the page
        self.browser.get(f'{self.live_server_url}/sunpeaks_webcams/')

        #wait for page to load
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "feedback-button"))
        )
        
        # Open the feedback modal
        feedback_button = self.browser.find_element(By.CLASS_NAME, "feedback-button")
        feedback_button.click()
        
        # Wait for the modal to be visible
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "feedback-modal"))
        )

        # Fill out the feedback form
        name_input = self.browser.find_element(By.ID, "name")
        email_input = self.browser.find_element(By.ID, "email")
        message_input = self.browser.find_element(By.ID, "message")

        name_input.send_keys("Test User")
        self.assertNotEqual(name_input.get_attribute("value"), "")
        
        email_input.send_keys("testuser@example.com")
        self.assertNotEqual(email_input.get_attribute("value"), "")
        
        message_input.send_keys("This is a test feedback message.")
        self.assertNotEqual(message_input.get_attribute("value"), "")

        # Submit the feedback form
        submit_button = self.browser.find_element(By.CSS_SELECTOR, "#feedback-form button[type='submit']")
        submit_button.click()

        # Wait for the success message to be visible
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "feedback-success"))
        )

        # Check that the success message is displayed
        success_message = self.browser.find_element(By.ID, "feedback-success").text
        success_message_color = self.browser.find_element(By.ID, "feedback-success").value_of_css_property('color')
        self.assertIn("Thank you for your feedback!", success_message, "Success message not displayed or incorrect")
        self.assertEqual(success_message_color, 'rgba(0, 0, 0, 1)', "Success message text color is not black")
        

        # Wait for the modal to close after a delay
        WebDriverWait(self.browser, 5).until(
            EC.invisibility_of_element((By.ID, "feedback-modal"))
        )

        # Check that the modal is closed
        modal = self.browser.find_element(By.ID, "feedback-modal")
        self.assertFalse(modal.is_displayed(), "Modal did not close after feedback submission")
        
    def test_feedback_modal_cancel(self):
                #get snapshot of the page
        self.browser.get(f'{self.live_server_url}/sunpeaks_webcams/')

        #wait for page to load
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "feedback-button"))
        )
        
        # Open the feedback modal
        feedback_button = self.browser.find_element(By.CLASS_NAME, "feedback-button")
        feedback_button.click()
        
        # Wait for the modal to be visible
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "feedback-modal"))
        )
        
        #hit close button
        close_button = self.browser.find_element(By.ID, "feedback-modal-close")
        close_button.click()
        
        #wait for modal to close
        WebDriverWait(self.browser, 5).until(
            EC.invisibility_of_element((By.ID, "feedback-modal"))
        )
        
        # Check that the modal is closed
        modal = self.browser.find_element(By.ID, "feedback-modal")
        self.assertFalse(modal.is_displayed(), "Modal did not close after feedback submission")
