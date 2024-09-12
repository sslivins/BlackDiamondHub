from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
from .models import Item

class ItemModalTest(StaticLiveServerTestCase):

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
        image = Image.new('RGB', (100, 100), color='white')
        image_io = io.BytesIO()
        image.save(image_io, format='PNG')
        image_file = SimpleUploadedFile("test_image.png", image_io.getvalue(), content_type="image/png")

        # Create a sample item with the placeholder image
        self.item = Item.objects.create(
            name="Sample Item",
            description="This is a sample item",
            room="Living Room",
            desc_long="A long description of the sample item.",
            picture=image_file  # Assuming your model has a picture field
        )

    def test_modal_opens_and_displays_content_with_image(self):
        # Navigate to the inventory page
        self.browser.get(f'{self.live_server_url}/inventory/')

        # Find the item element and click to open the modal
        item_element = self.browser.find_element(By.ID, f'item-{self.item.id}')
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
        self.assertEqual(modal_title, "Sample Item")
        self.assertEqual(modal_description, "This is a sample item")
        self.assertEqual(modal_room, "Living Room")

        # Ensure the image source is not empty (the image is loaded)
        self.assertTrue(image_src.endswith('test_image.png'))

    def test_modal_close_functionality(self):
        # Navigate to the inventory page
        self.browser.get(f'{self.live_server_url}/inventory/')

        # Open the modal
        item_element = self.browser.find_element(By.ID, f'item-{self.item.id}')
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
