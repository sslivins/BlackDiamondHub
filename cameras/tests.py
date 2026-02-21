import json
from django.test import TestCase, Client, override_settings
from unittest.mock import patch, MagicMock, PropertyMock
from .views import get_go2rtc_streams, _register_streams_with_go2rtc
from .protect_api import (
    get_protect_cameras, clear_cache, _camera_name_to_stream_name,
    _fetch_cameras_from_protect,
)


# --- Protect API helper tests ---

class CameraNameToStreamNameTests(TestCase):
    """Tests for the stream name conversion helper."""

    def test_spaces_become_underscores(self):
        self.assertEqual(_camera_name_to_stream_name("Front Door"), "front_door")

    def test_hyphens_become_underscores(self):
        self.assertEqual(_camera_name_to_stream_name("Back-Yard"), "back_yard")

    def test_mixed_formatting(self):
        self.assertEqual(
            _camera_name_to_stream_name("Front Door - Cam 1"),
            "front_door___cam_1",
        )

    def test_already_lowercase(self):
        self.assertEqual(_camera_name_to_stream_name("garage"), "garage")


# --- Protect API fetch tests ---

MOCK_BOOTSTRAP = {
    'nvr': {
        'ports': {'rtsp': 7447, 'rtsps': 7441},
    },
    'cameras': [
        {
            'name': 'Front Door',
            'connectionHost': '192.168.10.1',
            'channels': [
                {
                    'id': 0,
                    'name': 'High',
                    'isRtspEnabled': True,
                    'rtspAlias': 'abc123high',
                    'width': 2688,
                    'height': 1512,
                },
                {
                    'id': 1,
                    'name': 'Medium',
                    'isRtspEnabled': True,
                    'rtspAlias': 'abc123med',
                    'width': 1024,
                    'height': 576,
                },
            ],
        },
        {
            'name': 'Backyard',
            'connectionHost': '192.168.10.1',
            'channels': [
                {
                    'id': 0,
                    'name': 'High',
                    'isRtspEnabled': True,
                    'rtspAlias': 'xyz789high',
                    'width': 2688,
                    'height': 1512,
                },
            ],
        },
    ],
}


@override_settings(
    UNIFI_PROTECT_HOST='192.168.10.1',
    UNIFI_PROTECT_USERNAME='testuser',
    UNIFI_PROTECT_PASSWORD='testpass',
)
class FetchCamerasFromProtectTests(TestCase):
    """Tests for _fetch_cameras_from_protect."""

    def setUp(self):
        clear_cache()

    @patch('cameras.protect_api.requests.Session')
    def test_returns_cameras_sorted_by_name(self, MockSession):
        """Cameras are returned sorted alphabetically."""
        session = MockSession.return_value
        login_resp = MagicMock()
        login_resp.headers = {'x-csrf-token': 'tok123'}
        bootstrap_resp = MagicMock()
        bootstrap_resp.json.return_value = MOCK_BOOTSTRAP
        session.post.return_value = login_resp
        session.get.return_value = bootstrap_resp

        cameras = _fetch_cameras_from_protect()

        self.assertEqual(len(cameras), 2)
        self.assertEqual(cameras[0]['name'], 'Backyard')
        self.assertEqual(cameras[1]['name'], 'Front Door')

    @patch('cameras.protect_api.requests.Session')
    def test_constructs_rtsps_url(self, MockSession):
        """RTSP URLs are built correctly from bootstrap data."""
        session = MockSession.return_value
        login_resp = MagicMock()
        login_resp.headers = {'x-csrf-token': 'tok'}
        bootstrap_resp = MagicMock()
        bootstrap_resp.json.return_value = MOCK_BOOTSTRAP
        session.post.return_value = login_resp
        session.get.return_value = bootstrap_resp

        cameras = _fetch_cameras_from_protect()

        self.assertEqual(
            cameras[1]['rtsp_url'],
            'rtsps://192.168.10.1:7441/abc123high',
        )

    @patch('cameras.protect_api.requests.Session')
    def test_uses_first_rtsp_enabled_channel(self, MockSession):
        """Picks the first RTSP-enabled channel (highest quality)."""
        session = MockSession.return_value
        login_resp = MagicMock()
        login_resp.headers = {}
        bootstrap_resp = MagicMock()
        bootstrap_resp.json.return_value = MOCK_BOOTSTRAP
        session.post.return_value = login_resp
        session.get.return_value = bootstrap_resp

        cameras = _fetch_cameras_from_protect()

        # Front Door has two enabled channels — should use first (High)
        front_door = next(c for c in cameras if c['name'] == 'Front Door')
        self.assertIn('abc123high', front_door['rtsp_url'])

    @patch('cameras.protect_api.requests.Session')
    def test_skips_cameras_without_rtsp(self, MockSession):
        """Cameras with no RTSP-enabled channels are excluded."""
        bootstrap = {
            'nvr': {'ports': {'rtsps': 7441}},
            'cameras': [
                {
                    'name': 'NoRTSP Cam',
                    'connectionHost': '192.168.10.1',
                    'channels': [
                        {'id': 0, 'isRtspEnabled': False, 'rtspAlias': None},
                    ],
                },
            ],
        }
        session = MockSession.return_value
        login_resp = MagicMock()
        login_resp.headers = {}
        bootstrap_resp = MagicMock()
        bootstrap_resp.json.return_value = bootstrap
        session.post.return_value = login_resp
        session.get.return_value = bootstrap_resp

        cameras = _fetch_cameras_from_protect()

        self.assertEqual(cameras, [])

    @patch('cameras.protect_api.requests.Session')
    def test_returns_none_on_auth_failure(self, MockSession):
        """Returns None when authentication fails."""
        session = MockSession.return_value
        import requests
        session.post.side_effect = requests.RequestException("401 Unauthorized")

        result = _fetch_cameras_from_protect()

        self.assertIsNone(result)

    @override_settings(UNIFI_PROTECT_HOST='', UNIFI_PROTECT_USERNAME='', UNIFI_PROTECT_PASSWORD='')
    def test_returns_none_when_not_configured(self):
        """Returns None when Protect credentials are not set."""
        result = _fetch_cameras_from_protect()

        self.assertIsNone(result)

    @patch('cameras.protect_api.requests.Session')
    def test_generates_stream_name(self, MockSession):
        """Stream names are generated from camera names."""
        session = MockSession.return_value
        login_resp = MagicMock()
        login_resp.headers = {}
        bootstrap_resp = MagicMock()
        bootstrap_resp.json.return_value = MOCK_BOOTSTRAP
        session.post.return_value = login_resp
        session.get.return_value = bootstrap_resp

        cameras = _fetch_cameras_from_protect()

        front_door = next(c for c in cameras if c['name'] == 'Front Door')
        self.assertEqual(front_door['stream_name'], 'front_door')

    @patch('cameras.protect_api.requests.Session')
    def test_handles_dict_format_cameras(self, MockSession):
        """Handles bootstrap where cameras is a dict keyed by ID."""
        bootstrap = {
            'nvr': {'ports': {'rtsps': 7441}},
            'cameras': {
                'cam1': {
                    'name': 'Garage',
                    'connectionHost': '192.168.10.1',
                    'channels': [
                        {'id': 0, 'isRtspEnabled': True, 'rtspAlias': 'garageAlias'},
                    ],
                },
            },
        }
        session = MockSession.return_value
        login_resp = MagicMock()
        login_resp.headers = {}
        bootstrap_resp = MagicMock()
        bootstrap_resp.json.return_value = bootstrap
        session.post.return_value = login_resp
        session.get.return_value = bootstrap_resp

        cameras = _fetch_cameras_from_protect()

        self.assertEqual(len(cameras), 1)
        self.assertEqual(cameras[0]['name'], 'Garage')


# --- Cache tests ---

@override_settings(
    UNIFI_PROTECT_HOST='192.168.10.1',
    UNIFI_PROTECT_USERNAME='user',
    UNIFI_PROTECT_PASSWORD='pass',
)
class ProtectCachingTests(TestCase):
    """Tests for the camera list caching."""

    def setUp(self):
        clear_cache()

    @patch('cameras.protect_api._fetch_cameras_from_protect')
    def test_caches_result(self, mock_fetch):
        """Second call uses cached result, doesn't re-fetch."""
        mock_fetch.return_value = [{'name': 'Cam1', 'stream_name': 'cam1', 'rtsp_url': 'rtsps://x'}]

        result1 = get_protect_cameras()
        result2 = get_protect_cameras()

        mock_fetch.assert_called_once()
        self.assertEqual(result1, result2)

    @patch('cameras.protect_api._fetch_cameras_from_protect')
    def test_returns_empty_list_on_failure(self, mock_fetch):
        """Returns empty list when fetch fails (returns None)."""
        mock_fetch.return_value = None

        result = get_protect_cameras()

        self.assertEqual(result, [])

    def test_clear_cache(self):
        """clear_cache resets the internal cache."""
        from cameras.protect_api import _cache
        _cache['cameras'] = [{'name': 'test'}]
        _cache['timestamp'] = 9999999999

        clear_cache()

        self.assertIsNone(_cache['cameras'])
        self.assertEqual(_cache['timestamp'], 0)


# --- go2rtc fallback stream tests ---

class GetGo2rtcStreamsTests(TestCase):
    """Tests for the go2rtc fallback stream fetcher."""

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


# --- View tests ---

@override_settings(
    GO2RTC_URL='http://localhost:1984',
    UNIFI_PROTECT_HOST='192.168.10.1',
    UNIFI_PROTECT_USERNAME='user',
    UNIFI_PROTECT_PASSWORD='pass',
)
class CameraFeedViewWithProtectTests(TestCase):
    """Tests for camera_feed_view when Protect is configured."""

    def setUp(self):
        self.client = Client()
        clear_cache()

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_view_returns_200(self, mock_cameras, mock_register):
        """Camera page returns 200."""
        mock_cameras.return_value = []

        response = self.client.get("/cameras/")

        self.assertEqual(response.status_code, 200)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_view_uses_protect_cameras(self, mock_cameras, mock_register):
        """Streams come from Protect API, not go2rtc fallback."""
        mock_cameras.return_value = [
            {'name': 'Front Door', 'stream_name': 'front_door', 'rtsp_url': 'rtsps://x'},
        ]

        response = self.client.get("/cameras/")

        self.assertEqual(len(response.context['streams']), 1)
        self.assertEqual(response.context['streams'][0]['display_name'], 'Front Door')

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_view_registers_streams_with_go2rtc(self, mock_cameras, mock_register):
        """Discovered cameras are registered with go2rtc."""
        cameras = [
            {'name': 'Front Door', 'stream_name': 'front_door', 'rtsp_url': 'rtsps://x'},
        ]
        mock_cameras.return_value = cameras

        self.client.get("/cameras/")

        mock_register.assert_called_once_with('http://localhost:1984', cameras)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_view_shows_no_cameras_message(self, mock_cameras, mock_register):
        """Shows 'No Cameras Available' when Protect returns no cameras."""
        mock_cameras.return_value = []

        response = self.client.get("/cameras/")

        self.assertContains(response, "No Cameras Available")

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_view_renders_camera_iframes(self, mock_cameras, mock_register):
        """Renders iframe elements for each discovered camera."""
        mock_cameras.return_value = [
            {'name': 'Front Door', 'stream_name': 'front_door', 'rtsp_url': 'rtsps://x'},
            {'name': 'Backyard', 'stream_name': 'backyard', 'rtsp_url': 'rtsps://y'},
        ]

        response = self.client.get("/cameras/")

        self.assertContains(response, "Front Door")
        self.assertContains(response, "Backyard")
        self.assertContains(response, "stream.html?src=front_door")


@override_settings(
    GO2RTC_URL='http://localhost:1984',
    UNIFI_PROTECT_HOST='',
)
class CameraFeedViewFallbackTests(TestCase):
    """Tests for camera_feed_view when Protect is NOT configured (fallback)."""

    def setUp(self):
        self.client = Client()

    @patch("cameras.views.get_go2rtc_streams")
    def test_falls_back_to_go2rtc(self, mock_streams):
        """Uses go2rtc stream list when Protect is not configured."""
        mock_streams.return_value = [
            {'name': 'manual_cam', 'display_name': 'Manual Cam'},
        ]

        response = self.client.get("/cameras/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['streams']), 1)
        self.assertEqual(response.context['streams'][0]['name'], 'manual_cam')


# --- Stream registration tests ---

class RegisterStreamsTests(TestCase):
    """Tests for _register_streams_with_go2rtc."""

    @patch("cameras.views.urllib.request.urlopen")
    def test_registers_missing_streams(self, mock_urlopen):
        """Registers streams that don't exist in go2rtc yet."""
        # First call: GET existing streams (empty)
        get_resp = MagicMock()
        get_resp.read.return_value = json.dumps({}).encode()
        get_resp.__enter__ = lambda s: s
        get_resp.__exit__ = MagicMock(return_value=False)

        # Second call: PUT to register
        put_resp = MagicMock()
        put_resp.__enter__ = lambda s: s
        put_resp.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [get_resp, put_resp]

        cameras = [
            {'name': 'Front Door', 'stream_name': 'front_door', 'rtsp_url': 'rtsps://host:7441/abc'},
        ]

        _register_streams_with_go2rtc('http://localhost:1984', cameras)

        # Two calls: GET streams + PUT new stream
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("cameras.views.urllib.request.urlopen")
    def test_skips_existing_streams(self, mock_urlopen):
        """Does not re-register streams already in go2rtc."""
        get_resp = MagicMock()
        get_resp.read.return_value = json.dumps({
            "front_door": [{"url": "rtsps://host:7441/abc"}],
        }).encode()
        get_resp.__enter__ = lambda s: s
        get_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = get_resp

        cameras = [
            {'name': 'Front Door', 'stream_name': 'front_door', 'rtsp_url': 'rtsps://host:7441/abc'},
        ]

        _register_streams_with_go2rtc('http://localhost:1984', cameras)

        # Only one call: GET streams (no PUT needed)
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("cameras.views.urllib.request.urlopen")
    def test_handles_go2rtc_unreachable(self, mock_urlopen):
        """Gracefully handles go2rtc being unreachable."""
        mock_urlopen.side_effect = OSError("Connection refused")

        cameras = [
            {'name': 'Front Door', 'stream_name': 'front_door', 'rtsp_url': 'rtsps://host:7441/abc'},
        ]

        # Should not raise
        _register_streams_with_go2rtc('http://localhost:1984', cameras)
