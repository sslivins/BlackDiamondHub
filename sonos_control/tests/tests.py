from django.test import TestCase
from unittest.mock import patch


class SpotifySearchInputTest(TestCase):
    """Tests for touch-screen keyboard support on the Spotify search input."""

    @patch('sonos_control.views.sonos_get_speaker_info')
    def test_search_input_has_inputmode_none(self, mock_speakers):
        """The search input should have inputmode='none' to suppress the native keyboard in favour of the custom virtual keyboard."""
        mock_speakers.return_value = {}

        session = self.client.session
        session['spotify_token_info'] = {'access_token': 'fake-token'}
        session.save()

        response = self.client.get('/sonos_control/')
        content = response.content.decode()

        self.assertIn('inputmode="none"', content)

    @patch('sonos_control.views.sonos_get_speaker_info')
    def test_search_input_has_autocomplete_off(self, mock_speakers):
        """The search input should have autocomplete='off' to avoid browser suggestions covering the keyboard."""
        mock_speakers.return_value = {}

        session = self.client.session
        session['spotify_token_info'] = {'access_token': 'fake-token'}
        session.save()

        response = self.client.get('/sonos_control/')
        content = response.content.decode()

        self.assertIn('autocomplete="off"', content)

    @patch('sonos_control.views.sonos_get_speaker_info')
    def test_virtual_keyboard_present(self, mock_speakers):
        """The page should include the custom virtual keyboard container for touch-screen use."""
        mock_speakers.return_value = {}

        session = self.client.session
        session['spotify_token_info'] = {'access_token': 'fake-token'}
        session.save()

        response = self.client.get('/sonos_control/')
        content = response.content.decode()

        self.assertIn('id="virtual-keyboard"', content)
        self.assertIn('vk-container', content)
