from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.action_chains import ActionChains
from django.test import LiveServerTestCase
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
from .models import Item
import time

class ItemModalTest(LiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Set up Selenium Chrome WebDriver options (headless mode)
        options = Options()
        options.add_argument('--headless')  # Run Chrome in headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        cls.browser = webdriver.Chrome(options=options)
        cls.browser.set_window_size(1920, 1080)

        # Set an implicit wait for elements to load
        cls.browser.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def setUp(self):
        # Create a white square placeholder image in memory
        image = Image.new('RGB', (100, 100), color='black')
        image_io = io.BytesIO()
        image.save(image_io, format='PNG')

        #create 12 items and assign them to an array called items
        self.items = []
        for i in range(1, 13):
            image_file = SimpleUploadedFile(f'test_image_{i}.png', image_io.getvalue(), content_type="image/png")
          
            item = Item.objects.create(
                name=f"Item {i}",
                description=f"This is item {i}",
                room="Living Room",
                desc_long=f"A long description of item {i}.",
                picture=image_file
            )
            self.items.append(item)

    def test_modal_opens_and_displays_content_with_image(self):
        # Navigate to the inventory page
        self.browser.get(f'{self.live_server_url}/inventory/')
        
        #wait for first tile to load
        item_element = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((By.ID, f'item-{self.items[1].id}'))
        )
        
        item_element.click()
        
        # Wait for the modal to appear
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, 'itemModal'))
        )
        
        # Check modal content
        modal_title = self.browser.find_element(By.ID, 'modal-item-title').text
        modal_description = self.browser.find_element(By.ID, 'modal-item-description').text
        modal_room = self.browser.find_element(By.ID, 'modal-item-room').text

        # Check that the image is displayed in the modal
        modal_image = self.browser.find_element(By.ID, 'modal-item-image')
        image_src = modal_image.get_attribute('src')

        # Assert that the modal content matches the item data
        self.assertEqual(modal_title, "Item 2")
        self.assertEqual(modal_description, "This is item 2")
        self.assertEqual(modal_room, "Living Room")

        # Ensure the image source is not empty (the image is loaded)
        print(self.items[1].picture.url)
        self.assertTrue(image_src.endswith(self.items[1].picture.url))

    def test_modal_close_functionality(self):
        # Navigate to the inventory page
        self.browser.get(f'{self.live_server_url}/inventory/')

        # Open the modal
        #wait for first tile to load
        item_element = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((By.ID, f'item-{self.items[1].id}'))
        )
        item_element.click()

        # Wait for the modal to appear
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, 'itemModal'))
        )

        # Find and click the close button in the modal
        close_button = self.browser.find_element(By.CLASS_NAME, 'close')
        close_button.click()

        # Wait for the modal to be hidden
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((By.ID, 'itemModal'))
        )

        # Assert that the modal is no longer visible
        modal = self.browser.find_element(By.ID, 'itemModal')
        self.assertFalse(modal.is_displayed())
