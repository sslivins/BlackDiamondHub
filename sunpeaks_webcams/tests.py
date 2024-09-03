from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
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
            EC.visibility_of_element_located((By.ID, 'imageModal'))
        )

        modal = self.browser.find_element(By.ID, 'imageModal')
        self.assertTrue(modal.is_displayed(), "Modal did not open when the image was clicked")

    def test_modal_closes(self):
        self.browser.get(f'{self.live_server_url}/sunpeaks_webcams/')
        first_image = self.browser.find_element(By.CSS_SELECTOR, '#webcams img')
        first_image.click()

        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, 'imageModal'))
        )

        close_button = self.browser.find_element(By.CSS_SELECTOR, '#imageModal .close')
        close_button.click()

        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element((By.ID, 'imageModal'))
        )

        modal = self.browser.find_element(By.ID, 'imageModal')
        self.assertFalse(modal.is_displayed(), "Modal did not close when the close button was clicked")

