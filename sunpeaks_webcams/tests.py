from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import LiveServerTestCase
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import unittest

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
