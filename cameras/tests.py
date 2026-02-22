import json
from django.test import TestCase, Client, override_settings
from unittest.mock import patch, MagicMock, call
from .views import get_go2rtc_streams, _register_streams_with_go2rtc
from .protect_api import (
    get_protect_cameras, clear_cache, _camera_name_to_stream_name,
    _fetch_cameras_from_site, _is_ptz_camera, _get_ptz_preset_count,
    ptz_goto_preset,
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

# Mock camera list from GET /v1/cameras
MOCK_CAMERAS_RESPONSE = [
    {'id': 'cam_front', 'name': 'Front Door', 'state': 'CONNECTED'},
    {'id': 'cam_back', 'name': 'Backyard', 'state': 'CONNECTED'},
]

# Mock RTSPS stream responses from GET/POST /v1/cameras/{id}/rtsps-stream
MOCK_RTSPS_FRONT = {
    'high': 'rtsps://192.168.10.1:7441/abc123high',
    'medium': None,
    'low': 'rtsps://192.168.10.1:7441/abc123low',
}
MOCK_RTSPS_BACK = {
    'high': 'rtsps://192.168.10.1:7441/xyz789high',
    'medium': None,
    'low': 'rtsps://192.168.10.1:7441/xyz789low',
}
MOCK_RTSPS_EMPTY = {'high': None, 'medium': None, 'low': None}


def _make_mock_response(json_data, status_code=200):
    """Create a mock response object."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


def _make_ptz_not_supported_response():
    """Create a 400 response for non-PTZ cameras."""
    return _make_mock_response(
        {'error': 'Camera is not a type of PTZ'}, status_code=400,
    )


def _mock_get_side_effect(url, **kwargs):
    """Route mocked GET requests to correct responses."""
    if url.endswith('/cameras'):
        return _make_mock_response(MOCK_CAMERAS_RESPONSE)
    elif 'cam_front/rtsps-stream' in url:
        return _make_mock_response(MOCK_RTSPS_FRONT)
    elif 'cam_back/rtsps-stream' in url:
        return _make_mock_response(MOCK_RTSPS_BACK)
    return _make_mock_response(MOCK_RTSPS_EMPTY)


def _mock_post_non_ptz(url, **kwargs):
    """POST mock: all cameras return 400 (not PTZ)."""
    if '/ptz/' in url:
        return _make_ptz_not_supported_response()
    return _make_mock_response({}, status_code=200)


@override_settings(
    UNIFI_PROTECT_SITES=[{'host': '192.168.10.1', 'api_key': 'test_api_key', 'name': 'Test Site'}],
)
class FetchCamerasFromSiteTests(TestCase):
    """Tests for _fetch_cameras_from_site."""

    def setUp(self):
        clear_cache()

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_returns_cameras_sorted_by_name(self, mock_get, mock_post):
        """Cameras are returned sorted alphabetically."""
        mock_get.side_effect = _mock_get_side_effect
        mock_post.side_effect = _mock_post_non_ptz

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        self.assertEqual(len(cameras), 2)
        self.assertEqual(cameras[0]['name'], 'Backyard')
        self.assertEqual(cameras[1]['name'], 'Front Door')

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_returns_rtsps_urls(self, mock_get, mock_post):
        """RTSPS URLs are returned from the API."""
        mock_get.side_effect = _mock_get_side_effect
        mock_post.side_effect = _mock_post_non_ptz

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        front_door = next(c for c in cameras if c['name'] == 'Front Door')
        self.assertEqual(front_door['rtsp_url'], 'rtsps://192.168.10.1:7441/abc123high')
        self.assertEqual(front_door['rtsp_url_low'], 'rtsps://192.168.10.1:7441/abc123low')

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_creates_stream_when_none_exists(self, mock_get, mock_post):
        """Creates RTSPS stream via POST when GET returns null URLs."""
        def get_side_effect(url, **kwargs):
            if url.endswith('/cameras'):
                return _make_mock_response([
                    {'id': 'cam1', 'name': 'New Cam', 'state': 'CONNECTED'},
                ])
            return _make_mock_response(MOCK_RTSPS_EMPTY)

        def post_side_effect(url, **kwargs):
            if '/ptz/' in url:
                return _make_ptz_not_supported_response()
            return _make_mock_response({
                'high': 'rtsps://192.168.10.1:7441/newstream',
                'medium': None, 'low': None,
            })

        mock_get.side_effect = get_side_effect
        mock_post.side_effect = post_side_effect

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        self.assertEqual(len(cameras), 1)
        self.assertEqual(cameras[0]['rtsp_url'], 'rtsps://192.168.10.1:7441/newstream')
        # No low URL available in this case
        self.assertEqual(cameras[0]['rtsp_url_low'], '')

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_skips_cameras_without_rtsps_url(self, mock_get, mock_post):
        """Cameras where RTSPS stream creation fails are excluded."""
        import requests as req_lib

        def get_side_effect(url, **kwargs):
            if url.endswith('/cameras'):
                return _make_mock_response([
                    {'id': 'cam1', 'name': 'Broken Cam', 'state': 'CONNECTED'},
                ])
            return _make_mock_response(MOCK_RTSPS_EMPTY)

        mock_get.side_effect = get_side_effect
        mock_post.side_effect = req_lib.RequestException("Failed")

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        self.assertEqual(cameras, [])

    @patch('cameras.protect_api.requests.get')
    def test_returns_none_on_request_failure(self, mock_get):
        """Returns None when the camera list request fails."""
        import requests
        mock_get.side_effect = requests.RequestException("Connection refused")

        result = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        self.assertIsNone(result)

    def test_returns_none_when_not_configured(self):
        """Returns None when host/key are empty."""
        result = _fetch_cameras_from_site('', '')

        self.assertIsNone(result)

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_generates_stream_name(self, mock_get, mock_post):
        """Stream names are generated from camera names."""
        mock_get.side_effect = _mock_get_side_effect
        mock_post.side_effect = _mock_post_non_ptz

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        front_door = next(c for c in cameras if c['name'] == 'Front Door')
        self.assertEqual(front_door['stream_name'], 'front_door')

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_handles_dict_format_cameras(self, mock_get, mock_post):
        """Handles response where cameras is a dict keyed by ID."""
        def get_side_effect(url, **kwargs):
            if url.endswith('/cameras'):
                return _make_mock_response({
                    'cam1': {'id': 'cam1', 'name': 'Garage', 'state': 'CONNECTED'},
                })
            return _make_mock_response({
                'high': 'rtsps://192.168.10.1:7441/garageAlias',
                'medium': None, 'low': 'rtsps://192.168.10.1:7441/garageAliaslow',
            })

        mock_get.side_effect = get_side_effect
        mock_post.side_effect = _mock_post_non_ptz

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        self.assertEqual(len(cameras), 1)
        self.assertEqual(cameras[0]['name'], 'Garage')
        self.assertEqual(cameras[0]['rtsp_url_low'], 'rtsps://192.168.10.1:7441/garageAliaslow')

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_sends_api_key_header(self, mock_get, mock_post):
        """Verifies the API key is sent in the X-API-KEY header."""
        mock_get.side_effect = lambda url, **kwargs: _make_mock_response([])
        mock_get.return_value = _make_mock_response([])

        _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        first_call = mock_get.call_args_list[0]
        self.assertEqual(first_call.kwargs['headers']['X-API-KEY'], 'test_api_key')
        self.assertIn('/cameras', first_call.args[0])

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_strips_enable_srtp_from_url(self, mock_get, mock_post):
        """Strips ?enableSrtp from RTSPS URLs — go2rtc handles TLS natively."""
        def get_side_effect(url, **kwargs):
            if url.endswith('/cameras'):
                return _make_mock_response([
                    {'id': 'cam1', 'name': 'Cam', 'state': 'CONNECTED'},
                ])
            return _make_mock_response({
                'high': 'rtsps://192.168.10.1:7441/stream1?enableSrtp',
                'medium': None, 'low': 'rtsps://192.168.10.1:7441/stream1low?enableSrtp',
            })

        mock_get.side_effect = get_side_effect
        mock_post.side_effect = _mock_post_non_ptz

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        self.assertEqual(cameras[0]['rtsp_url'], 'rtsps://192.168.10.1:7441/stream1')
        self.assertEqual(cameras[0]['rtsp_url_low'], 'rtsps://192.168.10.1:7441/stream1low')

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_skips_cameras_without_id(self, mock_get, mock_post):
        """Cameras missing an ID field are skipped."""
        def get_side_effect(url, **kwargs):
            if url.endswith('/cameras'):
                return _make_mock_response([
                    {'name': 'No ID Cam', 'state': 'CONNECTED'},
                ])
            return _make_mock_response(MOCK_RTSPS_EMPTY)

        mock_get.side_effect = get_side_effect

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        self.assertEqual(cameras, [])


# --- Cache tests ---

@override_settings(
    UNIFI_PROTECT_SITES=[{'host': '192.168.10.1', 'api_key': 'test_api_key', 'name': 'Test Site'}],
)
class ProtectCachingTests(TestCase):
    """Tests for the camera list caching."""

    def setUp(self):
        clear_cache()

    @patch('cameras.protect_api._fetch_cameras_from_site')
    def test_caches_result(self, mock_fetch):
        """Second call uses cached result, doesn't re-fetch."""
        mock_fetch.return_value = [{'name': 'Cam1', 'stream_name': 'cam1', 'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low'}]

        result1 = get_protect_cameras()
        result2 = get_protect_cameras()

        mock_fetch.assert_called_once()
        self.assertEqual(result1, result2)

    @patch('cameras.protect_api._fetch_cameras_from_site')
    def test_returns_empty_list_on_failure(self, mock_fetch):
        """Returns site with empty cameras when fetch fails (returns None)."""
        mock_fetch.return_value = None

        result = get_protect_cameras()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['cameras'], [])

    def test_clear_cache(self):
        """clear_cache resets the internal cache."""
        from cameras.protect_api import _cache
        _cache['192.168.10.1'] = {'cameras': [{'name': 'test'}], 'timestamp': 9999999999}

        clear_cache()

        self.assertEqual(_cache, {})

    @override_settings(UNIFI_PROTECT_SITES=[])
    def test_returns_empty_list_when_no_sites(self):
        """Returns empty list when no sites are configured."""
        result = get_protect_cameras()

        self.assertEqual(result, [])


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
    UNIFI_PROTECT_SITES=[{'host': '192.168.10.1', 'api_key': 'test_api_key', 'name': 'Test Site'}],
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
        mock_cameras.return_value = [{'name': 'Test Site', 'host': '192.168.10.1', 'cameras': []}]

        response = self.client.get("/cameras/")

        self.assertEqual(response.status_code, 200)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_view_uses_protect_cameras(self, mock_cameras, mock_register):
        """Streams come from Protect API, not go2rtc fallback."""
        mock_cameras.return_value = [{
            'name': 'Test Site', 'host': '192.168.10.1',
            'cameras': [
                {'name': 'Front Door', 'stream_name': 'front_door',
                 'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low',
                 'camera_id': 'cam1', 'is_ptz': False, 'ptz_presets': 0},
            ],
        }]

        response = self.client.get("/cameras/")

        sites = response.context['sites']
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0]['name'], 'Test Site')
        self.assertEqual(len(sites[0]['streams']), 1)
        self.assertEqual(sites[0]['streams'][0]['display_name'], 'Front Door')

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_view_registers_streams_with_go2rtc(self, mock_cameras, mock_register):
        """Discovered cameras are registered with go2rtc."""
        cameras = [
            {'name': 'Front Door', 'stream_name': 'front_door',
             'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low',
             'camera_id': 'cam1', 'is_ptz': False, 'ptz_presets': 0},
        ]
        mock_cameras.return_value = [{
            'name': 'Test Site', 'host': '192.168.10.1', 'cameras': cameras,
        }]

        self.client.get("/cameras/")

        mock_register.assert_called_once_with('http://localhost:1984', cameras)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_view_shows_no_cameras_message(self, mock_cameras, mock_register):
        """Shows 'No Cameras Available' when Protect returns no cameras."""
        mock_cameras.return_value = [{'name': 'Test Site', 'host': '192.168.10.1', 'cameras': []}]

        response = self.client.get("/cameras/")

        self.assertContains(response, "No Cameras Available")

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_view_renders_camera_streams(self, mock_cameras, mock_register):
        """Renders video-stream elements for each discovered camera."""
        mock_cameras.return_value = [{
            'name': 'Test Site', 'host': '192.168.10.1',
            'cameras': [
                {'name': 'Front Door', 'stream_name': 'front_door',
                 'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low',
                 'camera_id': 'cam1', 'is_ptz': False, 'ptz_presets': 0},
                {'name': 'Backyard', 'stream_name': 'backyard',
                 'rtsp_url': 'rtsps://y', 'rtsp_url_low': 'rtsps://y_low',
                 'camera_id': 'cam2', 'is_ptz': False, 'ptz_presets': 0},
            ],
        }]

        response = self.client.get("/cameras/")
        content = response.content.decode()

        # Camera names are displayed
        self.assertContains(response, "Front Door")
        self.assertContains(response, "Backyard")
        # Uses the correct video-stream custom element (not video-rtc)
        self.assertIn("<video-stream", content)
        self.assertNotIn("<video-rtc", content)
        # Stream names stored as data attributes for dynamic URL construction
        self.assertIn('data-stream-name="front_door"', content)
        self.assertIn('data-stream-name="backyard"', content)
        # Low-quality flag is set
        self.assertIn('data-has-low="true"', content)
        # Properties set via JS using dynamic go2rtc base URL
        self.assertIn('el.dataset.streamName', content)
        # Loads the correct JS module (video-stream.js, not video-rtc.js)
        self.assertIn('video-stream.js', content)
        self.assertNotIn('video-rtc.js', content)
        # Each camera card has a touch overlay div for fullscreen
        self.assertEqual(content.count('class="cam-touch-overlay"'), 2)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_view_includes_fullscreen_overlay_and_js(self, mock_cameras, mock_register):
        """Touch overlay and fullscreen JS are present in the rendered page."""
        mock_cameras.return_value = [{
            'name': 'Test Site', 'host': '192.168.10.1',
            'cameras': [
                {'name': 'Front Door', 'stream_name': 'front_door',
                 'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low',
                 'camera_id': 'cam1', 'is_ptz': False, 'ptz_presets': 0},
            ],
        }]

        response = self.client.get("/cameras/")
        content = response.content.decode()

        # Touch overlay div sits above video for tap handling
        self.assertIn('class="cam-touch-overlay"', content)
        # Fullscreen toggle JS wired to the overlay
        self.assertIn('requestFullscreen', content)
        self.assertIn('exitFullscreen', content)
        self.assertIn('.cam-touch-overlay', content)
        # Stream quality management JS
        self.assertIn('fullscreenchange', content)
        self.assertIn('stopStreams', content)


@override_settings(
    GO2RTC_URL='http://localhost:1984',
    UNIFI_PROTECT_SITES=[],
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
        sites = response.context['sites']
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0]['name'], 'Cameras')
        self.assertEqual(len(sites[0]['streams']), 1)
        self.assertEqual(sites[0]['streams'][0]['name'], 'manual_cam')


# --- Stream registration tests ---

class RegisterStreamsTests(TestCase):
    """Tests for _register_streams_with_go2rtc."""

    @patch("cameras.views.urllib.request.urlopen")
    def test_registers_missing_streams(self, mock_urlopen):
        """Registers both high and low streams that don't exist in go2rtc."""
        # First call: GET existing streams (empty)
        get_resp = MagicMock()
        get_resp.read.return_value = json.dumps({}).encode()
        get_resp.__enter__ = lambda s: s
        get_resp.__exit__ = MagicMock(return_value=False)

        # PUT calls for high and low streams
        put_resp = MagicMock()
        put_resp.__enter__ = lambda s: s
        put_resp.__exit__ = MagicMock(return_value=False)

        put_resp2 = MagicMock()
        put_resp2.__enter__ = lambda s: s
        put_resp2.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [get_resp, put_resp, put_resp2]

        cameras = [
            {'name': 'Front Door', 'stream_name': 'front_door',
             'rtsp_url': 'rtsps://host:7441/abc',
             'rtsp_url_low': 'rtsps://host:7441/abc_low'},
        ]

        _register_streams_with_go2rtc('http://localhost:1984', cameras)

        # Three calls: GET streams + PUT high + PUT low
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch("cameras.views.urllib.request.urlopen")
    def test_skips_existing_streams(self, mock_urlopen):
        """Does not re-register streams already in go2rtc."""
        get_resp = MagicMock()
        get_resp.read.return_value = json.dumps({
            "front_door": [{"url": "rtsps://host:7441/abc"}],
            "front_door_low": [{"url": "rtsps://host:7441/abc_low"}],
        }).encode()
        get_resp.__enter__ = lambda s: s
        get_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = get_resp

        cameras = [
            {'name': 'Front Door', 'stream_name': 'front_door',
             'rtsp_url': 'rtsps://host:7441/abc',
             'rtsp_url_low': 'rtsps://host:7441/abc_low'},
        ]

        _register_streams_with_go2rtc('http://localhost:1984', cameras)

        # Only one call: GET streams (no PUTs needed)
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("cameras.views.urllib.request.urlopen")
    def test_handles_go2rtc_unreachable(self, mock_urlopen):
        """Gracefully handles go2rtc being unreachable."""
        mock_urlopen.side_effect = OSError("Connection refused")

        cameras = [
            {'name': 'Front Door', 'stream_name': 'front_door',
             'rtsp_url': 'rtsps://host:7441/abc',
             'rtsp_url_low': 'rtsps://host:7441/abc_low'},
        ]

        # Should not raise
        _register_streams_with_go2rtc('http://localhost:1984', cameras)


# --- PTZ API tests ---

class PtzDetectionTests(TestCase):
    """Tests for PTZ camera detection via probing."""

    @patch('cameras.protect_api.requests.post')
    def test_detects_ptz_camera(self, mock_post):
        """Returns True when camera responds 204 to goto."""
        mock_post.return_value = _make_mock_response({}, status_code=204)

        result = _is_ptz_camera('192.168.10.1', 'key', 'cam_ptz')

        self.assertTrue(result)
        self.assertIn('/ptz/goto/0', mock_post.call_args.args[0])

    @patch('cameras.protect_api.requests.post')
    def test_detects_non_ptz_camera(self, mock_post):
        """Returns False when camera responds 400."""
        mock_post.return_value = _make_ptz_not_supported_response()

        result = _is_ptz_camera('192.168.10.1', 'key', 'cam_fixed')

        self.assertFalse(result)

    @patch('cameras.protect_api.requests.post')
    def test_returns_false_on_network_error(self, mock_post):
        """Returns False when request fails."""
        import requests
        mock_post.side_effect = requests.RequestException("Timeout")

        result = _is_ptz_camera('192.168.10.1', 'key', 'cam1')

        self.assertFalse(result)


class PtzPresetCountTests(TestCase):
    """Tests for PTZ preset discovery."""

    @patch('cameras.protect_api.requests.post')
    def test_counts_valid_presets(self, mock_post):
        """Counts presets until 404 is returned."""
        def side_effect(url, **kwargs):
            # Slots 0-3 exist, slot 4 does not
            slot = int(url.rstrip('/').split('/')[-1])
            if slot < 4:
                return _make_mock_response({}, status_code=204)
            return _make_mock_response(
                {'error': "Entity 'preset' not found"}, status_code=404,
            )

        mock_post.side_effect = side_effect

        count = _get_ptz_preset_count('192.168.10.1', 'key', 'cam_ptz')

        self.assertEqual(count, 4)

    @patch('cameras.protect_api.requests.post')
    def test_returns_zero_when_no_presets(self, mock_post):
        """Returns 0 when even slot 0 fails."""
        mock_post.return_value = _make_mock_response(
            {'error': "Entity 'preset' not found"}, status_code=404,
        )

        count = _get_ptz_preset_count('192.168.10.1', 'key', 'cam_ptz')

        self.assertEqual(count, 0)

    @patch('cameras.protect_api.requests.post')
    def test_handles_network_error(self, mock_post):
        """Returns 0 on network error."""
        import requests
        mock_post.side_effect = requests.RequestException("Timeout")

        count = _get_ptz_preset_count('192.168.10.1', 'key', 'cam_ptz')

        self.assertEqual(count, 0)


@override_settings(
    UNIFI_PROTECT_SITES=[{'host': '192.168.10.1', 'api_key': 'test_api_key', 'name': 'Test Site'}],
)
class PtzGotoPresetTests(TestCase):
    """Tests for ptz_goto_preset."""

    def setUp(self):
        clear_cache()
        # Populate cache so _find_site_for_camera can find the host
        from cameras.protect_api import _cache
        _cache['192.168.10.1'] = {
            'cameras': [{'camera_id': 'cam_ptz', 'name': 'PTZ Cam'},
                        {'camera_id': 'cam_fixed', 'name': 'Fixed Cam'}],
            'timestamp': 9999999999,
        }

    @patch('cameras.protect_api.requests.post')
    def test_returns_true_on_success(self, mock_post):
        """Returns True when goto returns 204."""
        mock_post.return_value = _make_mock_response({}, status_code=204)

        result = ptz_goto_preset('cam_ptz', 2)

        self.assertTrue(result)

    @patch('cameras.protect_api.requests.post')
    def test_returns_false_on_failure(self, mock_post):
        """Returns False when goto returns non-204."""
        mock_post.return_value = _make_ptz_not_supported_response()

        result = ptz_goto_preset('cam_fixed', 0)

        self.assertFalse(result)

    @patch('cameras.protect_api.requests.post')
    def test_returns_false_on_network_error(self, mock_post):
        """Returns False on network error."""
        import requests
        mock_post.side_effect = requests.RequestException("Timeout")

        result = ptz_goto_preset('cam_ptz', 0)

        self.assertFalse(result)

    @override_settings(UNIFI_PROTECT_SITES=[])
    def test_returns_false_when_not_configured(self):
        """Returns False when Protect is not configured."""
        result = ptz_goto_preset('cam1', 0)

        self.assertFalse(result)


class FetchCamerasWithPtzTests(TestCase):
    """Tests for PTZ info in _fetch_cameras_from_site results."""

    def setUp(self):
        clear_cache()

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_non_ptz_cameras_have_is_ptz_false(self, mock_get, mock_post):
        """Non-PTZ cameras have is_ptz=False and ptz_presets=0."""
        mock_get.side_effect = _mock_get_side_effect
        mock_post.side_effect = _mock_post_non_ptz

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        for cam in cameras:
            self.assertFalse(cam['is_ptz'])
            self.assertEqual(cam['ptz_presets'], 0)

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_ptz_camera_detected_with_presets(self, mock_get, mock_post):
        """PTZ camera is detected and preset count is correct."""
        def get_side_effect(url, **kwargs):
            if url.endswith('/cameras'):
                return _make_mock_response([
                    {'id': 'cam_ptz', 'name': 'Hot Tub', 'state': 'CONNECTED'},
                ])
            return _make_mock_response({
                'high': 'rtsps://192.168.10.1:7441/hottub',
                'medium': None, 'low': 'rtsps://192.168.10.1:7441/hottublow',
            })

        def post_side_effect(url, **kwargs):
            if '/ptz/' not in url:
                return _make_ptz_not_supported_response()
            # PTZ probe: slots 0-2 exist, slot 3 does not
            slot_str = url.rstrip('/').split('/')[-1]
            try:
                slot = int(slot_str)
            except ValueError:
                return _make_mock_response({}, status_code=204)
            if slot < 3:
                return _make_mock_response({}, status_code=204)
            return _make_mock_response({}, status_code=404)

        mock_get.side_effect = get_side_effect
        mock_post.side_effect = post_side_effect

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        self.assertEqual(len(cameras), 1)
        self.assertTrue(cameras[0]['is_ptz'])
        self.assertEqual(cameras[0]['ptz_presets'], 3)
        self.assertEqual(cameras[0]['camera_id'], 'cam_ptz')

    @patch('cameras.protect_api.requests.post')
    @patch('cameras.protect_api.requests.get')
    def test_cameras_include_camera_id(self, mock_get, mock_post):
        """Cameras include their Protect camera_id."""
        mock_get.side_effect = _mock_get_side_effect
        mock_post.side_effect = _mock_post_non_ptz

        cameras = _fetch_cameras_from_site('192.168.10.1', 'test_api_key')

        self.assertEqual(cameras[0]['camera_id'], 'cam_back')
        self.assertEqual(cameras[1]['camera_id'], 'cam_front')


# --- PTZ View tests ---

@override_settings(
    GO2RTC_URL='http://localhost:1984',
    UNIFI_PROTECT_SITES=[{'host': '192.168.10.1', 'api_key': 'test_api_key', 'name': 'Test Site'}],
)
class PtzGotoViewTests(TestCase):
    """Tests for the ptz_goto view endpoint."""

    def setUp(self):
        self.client = Client()

    @patch('cameras.views.ptz_goto_preset')
    def test_successful_goto(self, mock_goto):
        """Returns success JSON on valid request."""
        mock_goto.return_value = True

        response = self.client.post(
            '/cameras/ptz/goto/',
            data=json.dumps({'camera_id': 'cam_ptz', 'slot': 2}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        mock_goto.assert_called_once_with('cam_ptz', 2)

    @patch('cameras.views.ptz_goto_preset')
    def test_failed_goto(self, mock_goto):
        """Returns success=false when goto fails."""
        mock_goto.return_value = False

        response = self.client.post(
            '/cameras/ptz/goto/',
            data=json.dumps({'camera_id': 'cam_fixed', 'slot': 0}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])

    def test_rejects_get(self):
        """GET requests are rejected (POST only)."""
        response = self.client.get('/cameras/ptz/goto/')

        self.assertEqual(response.status_code, 405)

    def test_rejects_missing_fields(self):
        """Missing camera_id or slot returns 400."""
        response = self.client.post(
            '/cameras/ptz/goto/',
            data=json.dumps({'camera_id': 'cam1'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_json(self):
        """Invalid JSON returns 400."""
        response = self.client.post(
            '/cameras/ptz/goto/',
            data='not json',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)


# --- PTZ template tests ---

@override_settings(
    GO2RTC_URL='http://localhost:1984',
    UNIFI_PROTECT_SITES=[{'host': '192.168.10.1', 'api_key': 'test_api_key', 'name': 'Test Site'}],
)
class PtzTemplateTests(TestCase):
    """Tests for PTZ controls in the camera template."""

    def setUp(self):
        self.client = Client()
        clear_cache()

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_ptz_buttons_shown_for_ptz_camera(self, mock_cameras, mock_register):
        """PTZ preset buttons appear for PTZ cameras."""
        mock_cameras.return_value = [{
            'name': 'Test Site', 'host': '192.168.10.1',
            'cameras': [
                {
                    'name': 'Hot Tub', 'stream_name': 'hot_tub',
                    'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low',
                    'camera_id': 'cam_ptz', 'is_ptz': True, 'ptz_presets': 4,
                },
            ],
        }]

        response = self.client.get("/cameras/")
        content = response.content.decode()

        self.assertIn('class="ptz-controls"', content)
        self.assertIn('class="ptz-btn"', content)
        # 4 preset buttons labeled 1-4
        self.assertEqual(content.count('class="ptz-btn"'), 4)
        self.assertIn('data-camera-id="cam_ptz"', content)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_no_ptz_buttons_for_non_ptz_camera(self, mock_cameras, mock_register):
        """Non-PTZ cameras do not get PTZ buttons."""
        mock_cameras.return_value = [{
            'name': 'Test Site', 'host': '192.168.10.1',
            'cameras': [
                {
                    'name': 'Front Door', 'stream_name': 'front_door',
                    'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low',
                    'camera_id': 'cam_front', 'is_ptz': False, 'ptz_presets': 0,
                },
            ],
        }]

        response = self.client.get("/cameras/")
        content = response.content.decode()

        self.assertNotIn('class="ptz-controls"', content)
        self.assertNotIn('class="ptz-btn"', content)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_ptz_js_sends_to_correct_endpoint(self, mock_cameras, mock_register):
        """PTZ JavaScript posts to the ptz_goto URL."""
        mock_cameras.return_value = [{
            'name': 'Test Site', 'host': '192.168.10.1',
            'cameras': [
                {
                    'name': 'Hot Tub', 'stream_name': 'hot_tub',
                    'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low',
                    'camera_id': 'cam_ptz', 'is_ptz': True, 'ptz_presets': 2,
                },
            ],
        }]

        response = self.client.get("/cameras/")
        content = response.content.decode()

        self.assertIn('/cameras/ptz/goto/', content)
        self.assertIn('X-CSRFToken', content)


# --- Multi-site tab tests ---

@override_settings(
    GO2RTC_URL='http://localhost:1984',
    UNIFI_PROTECT_SITES=[
        {'host': '192.168.10.1', 'api_key': 'key1', 'name': 'Sun Peaks'},
        {'host': '192.168.1.26', 'api_key': 'key2', 'name': 'Mercer Island'},
    ],
)
class MultiSiteTabTests(TestCase):
    """Tests for tabbed multi-site camera display."""

    def setUp(self):
        self.client = Client()
        clear_cache()

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_tabs_shown_for_multiple_sites(self, mock_cameras, mock_register):
        """Tab buttons appear when multiple sites are configured."""
        mock_cameras.return_value = [
            {'name': 'Sun Peaks', 'host': '192.168.10.1', 'cameras': []},
            {'name': 'Mercer Island', 'host': '192.168.1.26', 'cameras': []},
        ]

        response = self.client.get("/cameras/")
        content = response.content.decode()

        self.assertIn('class="site-tab', content)
        self.assertIn('Sun Peaks', content)
        self.assertIn('Mercer Island', content)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_no_tabs_for_single_site(self, mock_cameras, mock_register):
        """Tab buttons are hidden when only one site is configured."""
        mock_cameras.return_value = [
            {'name': 'Sun Peaks', 'host': '192.168.10.1', 'cameras': []},
        ]

        response = self.client.get("/cameras/")
        content = response.content.decode()

        self.assertNotIn('class="site-tab', content)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_each_site_has_own_panel(self, mock_cameras, mock_register):
        """Each site gets its own camera grid panel."""
        mock_cameras.return_value = [
            {
                'name': 'Sun Peaks', 'host': '192.168.10.1',
                'cameras': [
                    {'name': 'Front Door', 'stream_name': 'front_door',
                     'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low',
                     'camera_id': 'c1', 'is_ptz': False, 'ptz_presets': 0},
                ],
            },
            {
                'name': 'Mercer Island', 'host': '192.168.1.26',
                'cameras': [
                    {'name': 'Garage', 'stream_name': 'garage',
                     'rtsp_url': 'rtsps://y', 'rtsp_url_low': 'rtsps://y_low',
                     'camera_id': 'c2', 'is_ptz': False, 'ptz_presets': 0},
                ],
            },
        ]

        response = self.client.get("/cameras/")
        content = response.content.decode()

        self.assertIn('data-site="0"', content)
        self.assertIn('data-site="1"', content)
        self.assertIn('Front Door', content)
        self.assertIn('Garage', content)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_sites_passed_in_context(self, mock_cameras, mock_register):
        """Context contains sites list with correct structure."""
        mock_cameras.return_value = [
            {
                'name': 'Sun Peaks', 'host': '192.168.10.1',
                'cameras': [
                    {'name': 'Cam1', 'stream_name': 'cam1',
                     'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low',
                     'camera_id': 'c1', 'is_ptz': False, 'ptz_presets': 0},
                ],
            },
            {
                'name': 'Mercer Island', 'host': '192.168.1.26',
                'cameras': [],
            },
        ]

        response = self.client.get("/cameras/")

        sites = response.context['sites']
        self.assertEqual(len(sites), 2)
        self.assertEqual(sites[0]['name'], 'Sun Peaks')
        self.assertEqual(len(sites[0]['streams']), 1)
        self.assertEqual(sites[1]['name'], 'Mercer Island')
        self.assertEqual(len(sites[1]['streams']), 0)

    @patch("cameras.views._register_streams_with_go2rtc")
    @patch("cameras.views.get_protect_cameras")
    def test_registers_all_sites_with_go2rtc(self, mock_cameras, mock_register):
        """Cameras from all sites are registered with go2rtc."""
        cams1 = [
            {'name': 'Cam1', 'stream_name': 'cam1',
             'rtsp_url': 'rtsps://x', 'rtsp_url_low': 'rtsps://x_low',
             'camera_id': 'c1', 'is_ptz': False, 'ptz_presets': 0},
        ]
        cams2 = [
            {'name': 'Cam2', 'stream_name': 'cam2',
             'rtsp_url': 'rtsps://y', 'rtsp_url_low': 'rtsps://y_low',
             'camera_id': 'c2', 'is_ptz': False, 'ptz_presets': 0},
        ]
        mock_cameras.return_value = [
            {'name': 'Site 1', 'host': '192.168.10.1', 'cameras': cams1},
            {'name': 'Site 2', 'host': '192.168.1.26', 'cameras': cams2},
        ]

        self.client.get("/cameras/")

        self.assertEqual(mock_register.call_count, 2)
        mock_register.assert_any_call('http://localhost:1984', cams1)
        mock_register.assert_any_call('http://localhost:1984', cams2)
