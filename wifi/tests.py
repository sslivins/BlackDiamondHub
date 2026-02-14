from django.test import TestCase

import time
import base64
import io
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from django.contrib.auth.models import User

from django.test import TestCase, override_settings, Client
from django.urls import reverse

from PIL import Image
from pyzbar.pyzbar import decode

class WifiQRGenerationTests(TestCase):
    def setUp(self):
        self.client = Client()

    @override_settings(
        WIFI_NETWORKS_PUBLIC=["TestNetwork"],
        WIFI_PASSWORD_FOR_TESTNETWORK="testpass123",
    )
    def test_qr_code_generation_with_env_variables(self):
        # Access the QR view.
        response = self.client.get("/wifi/")
        self.assertEqual(response.status_code, 200)

        # Parse out the base64 image from the HTML.
        # For simplicity, we'll search for the first occurrence of a data URI.
        content = response.content.decode("utf-8")
        start = content.find("data:image/png;base64,")
        self.assertNotEqual(start, -1, "QR code base64 image not found")
        # Extract the base64 string
        base64_start = start + len("data:image/png;base64,")
        end = content.find("\"", base64_start)
        base64_str = content[base64_start:end]

        # Decode the base64 string into an image.
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))

        # Use pyzbar to decode the QR code.
        decoded_objects = decode(image)
        self.assertGreater(len(decoded_objects), 0, "No QR code detected in the image")

        # The expected QR text per your view format.
        #
        # Format: WIFI:S:<SSID>;T:WPA;P:<password>;;
        expected_qr_text = f"WIFI:S:TestNetwork;T:WPA;P:testpass123;;"
        decoded_text = decoded_objects[0].data.decode("utf-8")
        self.assertEqual(
            decoded_text,
            expected_qr_text,
            f"Expected QR data '{expected_qr_text}' but got '{decoded_text}'"
        )


@override_settings(
    WIFI_NETWORKS_PUBLIC=["TestNetwork","TestNetwork2"],
    WIFI_NETWORKS_AUTH=["TestNetworkAuth","TestNetworkAuth2"],
    WIFI_PASSWORD_FOR_TESTNETWORK="testpass123",
    WIFI_PASSWORD_FOR_TESTNETWORK2="testpass1232",
    WIFI_PASSWORD_FOR_TESTNETWORKAUTH="testpass1233",
    WIFI_PASSWORD_FOR_TESTNETWORKAUTH2="testpass1234",
)
class WifiQRPageSeleniumTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        # Initialize the Chrome webdriver.
        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.driver.set_window_size(1920, 1080)
        
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
        
    def setUp(self):
        # Reset browser state between tests
        self.driver.get('about:blank')
        self.driver.delete_all_cookies()

        self.test_user = User.objects.create_user(username='testuser', password='testpassword')
        
    def test_wifi_page_background_color(self):
        """Verify that the wifi page background color is black (rgba(0, 0, 0, 1))."""
        self.driver.get(f'{self.live_server_url}/wifi/')
        body = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        background_color = body.value_of_css_property("background-color")
        self.assertEqual(background_color, 'rgba(0, 0, 0, 1)')
        
    def test_wifi_page_title_and_header(self):
        """Verify that the wifi page title and header are correct."""
        self.driver.get(f'{self.live_server_url}/wifi/')
        header = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        self.assertEqual(header.text.strip(), "WiFi Networks")
        
    # def test_qr_codes_container_is_centered(self):
    #     """
    #     Verify that the container holding the QR codes is centered both vertically and horizontally.
    #     """
    #     self.driver.get(f'{self.live_server_url}/wifi/')
        
    #     self.driver.save_screenshot("screenshot.png")
        
    #     # Wait for the container to be present. Adjust the selector if necessary.
    #     container = self.driver.find_element(By.CSS_SELECTOR, '.container.full-height')
        
    #     # Get the container's bounding rectangle.
    #     container_rect = container.rect  # returns {'height': ..., 'width': ..., 'x': ..., 'y': ...}
        
    #     # Get the window size.
    #     window_size = self.driver.get_window_size()  # returns dict with keys 'width' and 'height'
        
    #     # Calculate expected x and y positions for centering.
    #     expected_x = (window_size['width'] - container_rect['width']) / 2
    #     expected_y = (window_size['height'] - container_rect['height']) / 2
        
    #     # Allow a small tolerance for differences due to rendering.
    #     tolerance = 10  # pixels
        
    #     self.assertAlmostEqual(
    #         container_rect['x'], 
    #         expected_x, 
    #         delta=tolerance, 
    #         msg=f"Container is not centered horizontally. Expected x ~{expected_x}, got {container_rect['x']}"
    #     )
        
    #     self.assertAlmostEqual(
    #         container_rect['y'], 
    #         expected_y, 
    #         delta=tolerance, 
    #         msg=f"Container is not centered vertically. Expected y ~{expected_y}, got {container_rect['y']}"
    #     )        
        
    def test_wifi_page_no_auth_qr_codes(self):
        """Verify that no QR codes for authenticated networks are displayed for unauthenticated users."""
        self.driver.get(f'{self.live_server_url}/wifi/')
        # Wait for QR code images to load
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.qr-code"))
        )
        # Find all QR code images.
        qr_images = self.driver.find_elements(By.CSS_SELECTOR, "img.qr-code")
        self.assertGreater(len(qr_images), 0, "No QR code images found on the page")
        
        # Define the expected auth QR texts that should NOT be present.
        auth_qr_texts = {
            f"WIFI:S:TestNetworkAuth;T:WPA;P:testpass1233;;",
            f"WIFI:S:TestNetworkAuth2;T:WPA;P:testpass1234;;"
        }
        
        # Iterate through each found QR code image.
        for img in qr_images:
            # Extract the base64 encoded image data.
            src = img.get_attribute("src")
            base64_str = src.split(",")[1]
            image_data = base64.b64decode(base64_str)
            image = Image.open(io.BytesIO(image_data))
            
            # Decode the QR code.
            decoded_objects = decode(image)
            self.assertGreater(len(decoded_objects), 0, "No QR code detected in the image")
            decoded_text = decoded_objects[0].data.decode("utf-8")
            
            # Ensure no auth network QR data is present.
            self.assertNotIn(
                decoded_text,
                auth_qr_texts,
                f"Auth QR code '{decoded_text}' should not be displayed for non-authenticated users"
            )
        
    def test_wifi_page_public_qr_code(self):
        """Verify that the public QR code is displayed correctly."""
        self.driver.get(f'{self.live_server_url}/wifi/')
        
        # Wait for QR code images to load
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.qr-code"))
        )
        # Verify that at least one QR code image is present.
        qr_images = self.driver.find_elements(By.CSS_SELECTOR, "img.qr-code")
        self.assertGreater(len(qr_images), 0, "No QR code images found on the page")
        
        # Optionally, assert that each found image has valid dimensions and correct QR data.
        expected_qr_texts = {
            f"WIFI:S:TestNetwork;T:WPA;P:testpass123;;",
            f"WIFI:S:TestNetwork2;T:WPA;P:testpass1232;;"
        }
        found_qr_texts = set()

        for img in qr_images:
            # Ensure the image has non-zero width.
            width = img.size.get("width", 0)
            self.assertGreater(width, 0, f"Image width should be > 0 but got {width}")

            # Check if the image is a valid QR code.
            src = img.get_attribute("src")
            base64_str = src.split(",")[1]
            image_data = base64.b64decode(base64_str)
            image = Image.open(io.BytesIO(image_data))
            decoded_objects = decode(image)
            self.assertGreater(len(decoded_objects), 0, "No QR code detected in the image")

            # Check if the decoded text is correct.
            decoded_text = decoded_objects[0].data.decode("utf-8")
            self.assertIn(
                decoded_text,
                expected_qr_texts,
                f"Decoded QR text '{decoded_text}' not one of the expected values."
            )
            found_qr_texts.add(decoded_text)

        # Verify that we found all expected QR codes.
        self.assertEqual(found_qr_texts, expected_qr_texts, "Not all expected QR codes were found.")
        
    def test_wifi_page_login_redirects_back_to_wifi(self):
        """
        Test that after logging in, the user is redirected back to the wifi page.
        """
       
        self.driver.get(f"{self.live_server_url}/wifi/")
        
        #press the login button
        login_button = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.ID, 'login-button'))
        )
        #assert if login button is present
        self.assertTrue(login_button.is_displayed(), "Login button is not displayed")
        login_button.click()
        
        # Wait for login page to load
        username_input = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.ID, "id_username"))
        )
        password_input = self.driver.find_element(By.ID, "id_password")
        username_input.send_keys("testuser")
        password_input.send_keys("testpassword")
        
        login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for redirect back to wifi page
        WebDriverWait(self.driver, 20).until(
            EC.url_contains("/wifi/")
        )
        
        # Check that the current URL is the wifi page.
        self.assertIn("/wifi/", self.driver.current_url)
        
    def test_wifi_page_logout_redirects_back_to_wifi(self):
        """
        Test that after logging out, the user is redirected back to the wifi page.
        """
     
        self.driver.get(f"{self.live_server_url}/wifi/")
        
        #press the login button
        login_button = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.ID, 'login-button'))
        )
        #assert if login button is present
        self.assertTrue(login_button.is_displayed(), "Login button is not displayed")
        login_button.click()
        
        # Wait for login page to load
        username_input = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.ID, "id_username"))
        )
        password_input = self.driver.find_element(By.ID, "id_password")
        username_input.send_keys("testuser")
        password_input.send_keys("testpassword")
        
        login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for the redirect to complete.
        logout_button = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.ID, 'logout-button'))
        )
        #assert if logout button is present
        self.assertTrue(logout_button.is_displayed(), "Logout button is not displayed")
        logout_button.click()
        
        # Check that the current URL is the wifi page.
        self.assertIn("/wifi/", self.driver.current_url)
        
    def test_wifi_page_no_public_qr_codes(self):
        """
        Log in a test user and verify that none of the public QR codes are present.
        """
       
        self.driver.get(f"{self.live_server_url}/wifi/")
        
        login_button = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.ID, 'login-button'))
        )
        #assert if login button is present
        self.assertTrue(login_button.is_displayed(), "Login button is not displayed")
        login_button.click()
        
        # Wait for login page to load
        username_input = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.ID, "id_username"))
        )
        password_input = self.driver.find_element(By.ID, "id_password")
        username_input.send_keys("testuser")
        password_input.send_keys("testpassword")
        
        login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for redirect back to wifi page and QR codes to load
        WebDriverWait(self.driver, 20).until(
            EC.url_contains("/wifi/")
        )
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.qr-code"))
        )
    
        qr_images = self.driver.find_elements(By.CSS_SELECTOR, "img.qr-code")
        self.assertGreater(len(qr_images), 0, "No QR code images found on the page")
        
        # Define the expected public QR texts that should NOT be present after login.
        public_qr_texts = {
            f"WIFI:S:TestNetwork;T:WPA;P:testpass123;;",
            f"WIFI:S:TestNetwork2;T:WPA;P:testpass1232;;"
        }
        
        for img in qr_images:
            src = img.get_attribute("src")
            base64_str = src.split(",")[1]
            image_data = base64.b64decode(base64_str)
            image = Image.open(io.BytesIO(image_data))
            
            # Decode the QR code.
            decoded_objects = decode(image)
            self.assertGreater(len(decoded_objects), 0, "No QR code detected in the image")
            decoded_text = decoded_objects[0].data.decode("utf-8")

            # Ensure that the decoded text is not one of the public QR codes.
            self.assertNotIn(
                decoded_text,
                public_qr_texts,
                f"Public QR code '{decoded_text}' should not be displayed for authenticated users"
            )        
        
    
    def test_wifi_page_auth_qr_codes(self):
        """
        Log in a test user and verify that the auth QR codes are present.
        """
        
        self.driver.get(f"{self.live_server_url}/wifi/")
        
        login_button = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.ID, 'login-button'))
        )
        #assert if login button is present
        self.assertTrue(login_button.is_displayed(), "Login button is not displayed")
        login_button.click()
        
        # Wait for login page to load
        username_input = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.ID, "id_username"))
        )
        password_input = self.driver.find_element(By.ID, "id_password")
        username_input.send_keys("testuser")
        password_input.send_keys("testpassword")
        
        login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for redirect back to wifi page
        WebDriverWait(self.driver, 20).until(
            EC.url_contains("/wifi/")
        )   
        
        
        qr_images = self.driver.find_elements(By.CSS_SELECTOR, "img.qr-code")
        self.assertGreater(len(qr_images), 0, "No QR code images found on the page")
        
        # Expected auth QR texts based on overridden settings.
        expected_auth_qr_texts = {
            f"WIFI:S:TestNetworkAuth;T:WPA;P:testpass1233;;",
            f"WIFI:S:TestNetworkAuth2;T:WPA;P:testpass1234;;"
        }
        found_auth_qr_texts = set()
        
        for img in qr_images:
            src = img.get_attribute("src")
            base64_str = src.split(",")[1]
            image_data = base64.b64decode(base64_str)
            image = Image.open(io.BytesIO(image_data))

            # Decode the QR code.
            decoded_objects = decode(image)
            self.assertGreater(len(decoded_objects), 0, "No QR code detected in the image")
            decoded_text = decoded_objects[0].data.decode("utf-8")
            
            if decoded_text in expected_auth_qr_texts:
                found_auth_qr_texts.add(decoded_text)
        
        self.assertEqual(
            found_auth_qr_texts,
            expected_auth_qr_texts,
            "Not all expected auth QR codes were found on the logged in page."
        )            