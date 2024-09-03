from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.test import LiveServerTestCase
from selenium.webdriver.chrome.options import Options
from django.contrib.auth.models import User

class WeatherUnitToggleTest(LiveServerTestCase):
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
        cls.browser.implicitly_wait(20)

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def test_temperature_non_number(self):
        self.browser.get(self.live_server_url)
        
        toggle_button = WebDriverWait(self.browser, 20).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'toggle-button'))
        )
        WebDriverWait(self.browser, 20).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'toggle-button'))
        )        
        
        self.browser.execute_script('''
            document.querySelector(".temperature").setAttribute("data-metric", "N/A");
            document.querySelector(".temperature").textContent = "N/A°C";
        ''')
        
        #self.browser.save_screenshot('screenshot.png')
        
        toggle_button.click()
        
        temperature_text = self.browser.find_element(By.CLASS_NAME, "temperature").text
        self.assertEqual(temperature_text, "N/A°C")
        toggle_button.click()
        temperature_text = self.browser.find_element(By.CLASS_NAME, "temperature").text
        self.assertEqual(temperature_text, "N/A°C")

    def test_temperature_missing(self):
        self.browser.get(self.live_server_url)
        self.browser.execute_script('''
            document.querySelector(".temperature").setAttribute("data-metric", "");
            document.querySelector(".temperature").textContent = "°C";
        ''')
        toggle_button = self.browser.find_element(By.CLASS_NAME, "toggle-button")
        toggle_button.click()
        temperature_text = self.browser.find_element(By.CLASS_NAME, "temperature").text
        self.assertEqual(temperature_text, "°C")
        toggle_button.click()
        temperature_text = self.browser.find_element(By.CLASS_NAME, "temperature").text
        self.assertEqual(temperature_text, "°C")

    def test_temperature_conversion_c_to_f(self):
        self.browser.get(self.live_server_url)
        self.browser.execute_script('''
            document.querySelector(".temperature").setAttribute("data-metric", "25");
            document.querySelector(".temperature").textContent = "25°C";
        ''')
        toggle_button = self.browser.find_element(By.CLASS_NAME, "toggle-button")
        toggle_button.click()
        temperature_text = self.browser.find_element(By.CLASS_NAME, "temperature").text
        self.assertEqual(temperature_text, "77°F")  # 25°C -> 77°F
        toggle_button.click()
        temperature_text = self.browser.find_element(By.CLASS_NAME, "temperature").text
        self.assertEqual(temperature_text, "25°C")

    def test_elevation_conversion_m_to_ft(self):
        self.browser.get(self.live_server_url)
        self.browser.execute_script('''
            document.querySelector(".elevation").setAttribute("data-metric", "1000");
            document.querySelector(".elevation").textContent = "Elevation: 1000 m";
        ''')
        toggle_button = self.browser.find_element(By.CLASS_NAME, "toggle-button")
        toggle_button.click()
        elevation_text = self.browser.find_element(By.CLASS_NAME, "elevation").text
        self.assertEqual(elevation_text, "Elevation: 3281 ft")  # 1000 meters -> 3281 feet
        toggle_button.click()
        elevation_text = self.browser.find_element(By.CLASS_NAME, "elevation").text
        self.assertEqual(elevation_text, "Elevation: 1000 m")

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
        # Create a test user
        cls.test_user = User.objects.create_user(username='testuser', password='testpassword', is_staff=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def test_feedback_modal_submission_and_unread_count(self):
        # Log in
        self.browser.get(self.live_server_url + '/accounts/login/')
        username_input = self.browser.find_element(By.ID, "id_username")
        password_input = self.browser.find_element(By.ID, "id_password")
        
        username_input.send_keys("testuser")
        password_input.send_keys("testpassword")
        
        login_button = self.browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()

        # Wait for the login to complete and redirect to the home page
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "feedback-button"))
        )
        
        # Capture the current unread message count
        try:
            unread_count_element = self.browser.find_element(By.CLASS_NAME, "badge")
            initial_unread_count = int(unread_count_element.text)
        except:
            initial_unread_count = 0

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
        email_input.send_keys("testuser@example.com")
        message_input.send_keys("This is a test feedback message.")

        # Submit the feedback form
        submit_button = self.browser.find_element(By.CSS_SELECTOR, "#feedback-form button[type='submit']")
        submit_button.click()

        # Wait for the success message to be visible
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "feedback-success"))
        )

        # Check that the success message is displayed
        success_message = self.browser.find_element(By.ID, "feedback-success").text
        self.assertIn("Thank you for your feedback!", success_message)

        # Wait for the modal to close after a delay
        WebDriverWait(self.browser, 5).until(
            EC.invisibility_of_element((By.ID, "feedback-modal"))
        )

        # Check if the unread message count increased
        WebDriverWait(self.browser, 10).until(
            EC.text_to_be_present_in_element((By.CLASS_NAME, "badge"), str(initial_unread_count + 1))
        )

        # Verify the unread count increased by 1
        new_unread_count_element = self.browser.find_element(By.CLASS_NAME, "badge")
        new_unread_count = int(new_unread_count_element.text)
        self.assertEqual(new_unread_count, initial_unread_count + 1)