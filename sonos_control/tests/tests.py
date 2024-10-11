from django.test import TestCase
from unittest.mock import patch
import json
import os

# Create your tests here.
from sonos_control.views import sonos_get_speaker_info  # Adjust the import path as needed

class SonosSpeakerInfoTest(TestCase):

    def setUp(self):
        # Load the mock data from the JSON file
        current_directory = os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(current_directory, 'sonos_speakers_info.json')

        with open(json_file_path, 'r') as json_file:
            self.mock_speaker_info = json.load(json_file)

    @patch('sonos_control.views.sonos_get_speaker_info')
    def test_sonos_speaker_info(self, mock_get_speaker_info):
        # Set the mock to return the mock data
        mock_get_speaker_info.return_value = self.mock_speaker_info

        # Now call the code that uses sonos_get_speaker_info()
        # For example, if you have a view that uses it:

        response = self.client.get('/your-sonos-endpoint/')  # Replace with your actual endpoint

        # Now you can assert that the response is as expected
        self.assertEqual(response.status_code, 200)
        # Add more assertions as needed
