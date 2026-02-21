import json
from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
from .views import get_go2rtc_streams


class GetGo2rtcStreamsTests(TestCase):
    """Tests for the get_go2rtc_streams helper function."""

    @patch("cameras.views.urllib.request.urlopen")
    def test_returns_sorted_streams(self, mock_urlopen):
        """Streams are returned sorted alphabetically with display names."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "front_door": [{"url": "rtsp://..."}],
            "backyard": [{"url": "rtsp://..."}],
            "driveway": [{"url": "rtsp://..."}],
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        streams = get_go2rtc_streams("http://localhost:1984")

        self.assertEqual(len(streams), 3)
        self.assertEqual(streams[0]["name"], "backyard")
        self.assertEqual(streams[0]["display_name"], "Backyard")
        self.assertEqual(streams[1]["name"], "driveway")
        self.assertEqual(streams[2]["name"], "front_door")
        self.assertEqual(streams[2]["display_name"], "Front Door")

    @patch("cameras.views.urllib.request.urlopen")
    def test_returns_empty_on_connection_error(self, mock_urlopen):
        """Returns empty list when go2rtc is unreachable."""
        mock_urlopen.side_effect = OSError("Connection refused")

        streams = get_go2rtc_streams("http://localhost:1984")

        self.assertEqual(streams, [])

    @patch("cameras.views.urllib.request.urlopen")
    def test_returns_empty_on_invalid_json(self, mock_urlopen):
        """Returns empty list when go2rtc returns invalid JSON."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"not json"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        streams = get_go2rtc_streams("http://localhost:1984")

        self.assertEqual(streams, [])

    @patch("cameras.views.urllib.request.urlopen")
    def test_returns_empty_when_no_streams(self, mock_urlopen):
        """Returns empty list when go2rtc has no streams configured."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        streams = get_go2rtc_streams("http://localhost:1984")

        self.assertEqual(streams, [])

    @patch("cameras.views.urllib.request.urlopen")
    def test_display_name_formatting(self, mock_urlopen):
        """Stream names with underscores/hyphens are formatted as titles."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "back_yard_cam": [{"url": "rtsp://..."}],
            "front-porch": [{"url": "rtsp://..."}],
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        streams = get_go2rtc_streams("http://localhost:1984")

        self.assertEqual(streams[0]["display_name"], "Back Yard Cam")
        self.assertEqual(streams[1]["display_name"], "Front Porch")


class CameraFeedViewTests(TestCase):
    """Tests for the camera_feed_view."""

    def setUp(self):
        self.client = Client()

    @patch("cameras.views.get_go2rtc_streams")
    def test_view_returns_200(self, mock_get_streams):
        """Camera page returns 200."""
        mock_get_streams.return_value = []

        response = self.client.get("/cameras/")

        self.assertEqual(response.status_code, 200)

    @patch("cameras.views.get_go2rtc_streams")
    def test_view_renders_template(self, mock_get_streams):
        """Camera page uses the correct template."""
        mock_get_streams.return_value = []

        response = self.client.get("/cameras/")

        self.assertTemplateUsed(response, "camera_feeds.html")

    @patch("cameras.views.get_go2rtc_streams")
    def test_view_passes_streams_to_context(self, mock_get_streams):
        """Streams are passed to the template context."""
        mock_get_streams.return_value = [
            {"name": "front_door", "display_name": "Front Door"},
        ]

        response = self.client.get("/cameras/")

        self.assertEqual(len(response.context["streams"]), 1)
        self.assertEqual(response.context["streams"][0]["name"], "front_door")

    @patch("cameras.views.get_go2rtc_streams")
    def test_view_passes_go2rtc_url_to_context(self, mock_get_streams):
        """go2rtc URL is passed to the template context."""
        mock_get_streams.return_value = []

        response = self.client.get("/cameras/")

        self.assertIn("go2rtc_url", response.context)

    @patch("cameras.views.get_go2rtc_streams")
    def test_view_shows_no_cameras_message(self, mock_get_streams):
        """Shows 'no cameras' message when no streams available."""
        mock_get_streams.return_value = []

        response = self.client.get("/cameras/")

        self.assertContains(response, "No Cameras Available")

    @patch("cameras.views.get_go2rtc_streams")
    def test_view_renders_camera_iframes(self, mock_get_streams):
        """Renders iframe elements for each stream."""
        mock_get_streams.return_value = [
            {"name": "front_door", "display_name": "Front Door"},
            {"name": "backyard", "display_name": "Backyard"},
        ]

        response = self.client.get("/cameras/")

        self.assertContains(response, "Front Door")
        self.assertContains(response, "Backyard")
        self.assertContains(response, "stream.html?src=front_door")
        self.assertContains(response, "stream.html?src=backyard")
        self.assertContains(response, "<iframe", count=2)
