from django.test import TestCase
from unittest.mock import patch


class SpotifySearchInputTest(TestCase):
    """Tests for touch-screen keyboard support on the Spotify search input."""

    @patch('sonos_control.views.sonos_get_speaker_info')
    def test_search_input_has_inputmode_search(self, mock_speakers):
        """The search input should have inputmode='search' so touch devices show an on-screen keyboard."""
        mock_speakers.return_value = {}

        # Set session so the template thinks we're authenticated with Spotify
        session = self.client.session
        session['spotify_token_info'] = {'access_token': 'fake-token'}
        session.save()

        response = self.client.get('/sonos_control/')
        content = response.content.decode()

        self.assertIn('inputmode="search"', content)

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
