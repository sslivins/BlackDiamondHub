from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.test import LiveServerTestCase
from selenium.webdriver.chrome.options import Options

class WeatherUnitToggleTest(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        options = Options()
        options.add_argument('--headless')  # Run Chrome in headless mode
        options.add_argument('--no-sandbox')  # Bypass OS security model, necessary in some environments
        options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
        options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
        options.add_argument('--window-size=1920x1080')  # Set a standard window size for consistency
        cls.browser = webdriver.Chrome(options=options)
        cls.browser.implicitly_wait(10)   

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def test_temperature_non_number(self):
        self.browser.get(self.live_server_url)
        self.browser.execute_script('''
            document.querySelector(".temperature").setAttribute("data-metric", "N/A");
            document.querySelector(".temperature").textContent = "N/A°C";
        ''')
        toggle_button = self.browser.find_element(By.CLASS_NAME, "toggle-button")
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
