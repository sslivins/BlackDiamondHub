"""
Tests for the device_control app.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory, tag
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from .device_config import TABS, get_all_entity_ids
from .ha_client import get_entity_state, get_entity_states, call_service
from . import views

# The FILTERABLE_TABS set must stay in sync with the JS in the template.
FILTERABLE_TABS = {"lights", "shades"}


class DeviceConfigTests(TestCase):
    """Tests for device_config.py."""

    def test_tabs_not_empty(self):
        self.assertTrue(len(TABS) > 0)

    def test_each_tab_has_required_keys(self):
        for tab in TABS:
            self.assertIn("key", tab)
            self.assertIn("label", tab)
            self.assertIn("icon", tab)
            self.assertIn("devices", tab)

    def test_get_all_entity_ids_returns_set(self):
        ids = get_all_entity_ids()
        self.assertIsInstance(ids, set)
        self.assertTrue(len(ids) > 0)

    def test_all_entity_ids_have_dot(self):
        """Every entity_id should be in domain.object_id format."""
        for eid in get_all_entity_ids():
            self.assertIn(".", eid, f"Entity ID missing dot: {eid}")

    def test_no_duplicate_entity_ids_within_tab(self):
        """No tab should list the same entity_id twice."""
        for tab in TABS:
            seen = set()
            for _group, devices in tab["devices"].items():
                for dev in devices:
                    eid = dev["entity_id"]
                    self.assertNotIn(eid, seen, f"Duplicate {eid} in tab {tab['key']}")
                    seen.add(eid)


class HaClientTests(TestCase):
    """Tests for ha_client.py (mocked HTTP)."""

    @patch("device_control.ha_client.requests.get")
    def test_get_entity_state_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "entity_id": "switch.test",
            "state": "on",
            "attributes": {"friendly_name": "Test"},
        }
        mock_get.return_value = mock_resp

        result = get_entity_state("switch.test")
        self.assertIsNotNone(result)
        self.assertEqual(result["state"], "on")

    @patch("device_control.ha_client.requests.get")
    def test_get_entity_state_failure(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = get_entity_state("switch.nonexistent")
        self.assertIsNone(result)

    @patch("device_control.ha_client.requests.get")
    def test_get_entity_states_filters(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"entity_id": "switch.a", "state": "on", "attributes": {}},
            {"entity_id": "switch.b", "state": "off", "attributes": {}},
            {"entity_id": "switch.c", "state": "on", "attributes": {}},
        ]
        mock_get.return_value = mock_resp

        result = get_entity_states(["switch.a", "switch.c"])
        self.assertEqual(len(result), 2)
        self.assertIn("switch.a", result)
        self.assertIn("switch.c", result)
        self.assertNotIn("switch.b", result)

    @patch("device_control.ha_client.requests.post")
    def test_call_service_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        success, error = call_service("switch", "turn_on", "switch.test")
        self.assertTrue(success)
        self.assertIsNone(error)

    @patch("device_control.ha_client.requests.post")
    def test_call_service_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        success, error = call_service("switch", "turn_on", "switch.test")
        self.assertFalse(success)
        self.assertIn("500", error)


class ViewTests(TestCase):
    """Tests for device_control views."""

    def test_main_page_renders(self):
        resp = self.client.get(reverse("device_control"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Device Control")
        self.assertContains(resp, "dc-tab")

    def test_filter_bar_visible_on_initial_load(self):
        """The filter bar must not be hidden when the first tab is filterable."""
        first_tab_key = TABS[0]["key"]
        resp = self.client.get(reverse("device_control"))
        content = resp.content.decode()

        if first_tab_key in FILTERABLE_TABS:
            # Filter bar should NOT have the 'hidden' class
            self.assertNotIn(
                'dc-filter-bar hidden',
                content,
                "Filter bar is hidden on initial load but the first tab "
                f"('{first_tab_key}') is filterable — it should be visible.",
            )
        else:
            # Filter bar SHOULD have the 'hidden' class
            self.assertIn('dc-filter-bar hidden', content)

    def test_main_page_has_all_tabs(self):
        resp = self.client.get(reverse("device_control"))
        for tab in TABS:
            self.assertContains(resp, tab["label"])

    @patch("device_control.views.get_entity_states")
    def test_states_endpoint(self, mock_states):
        mock_states.return_value = {
            "switch.living_room_tv_socket_1": {
                "state": "on",
                "attributes": {"friendly_name": "Living Room TV Socket 1"},
            }
        }
        resp = self.client.get(reverse("device_control_states"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("switch.living_room_tv_socket_1", data)
        self.assertEqual(data["switch.living_room_tv_socket_1"]["state"], "on")

    def test_action_requires_post(self):
        resp = self.client.get(reverse("device_control_action"))
        self.assertEqual(resp.status_code, 405)

    @patch("device_control.views.call_service")
    def test_action_toggle_switch(self, mock_call):
        mock_call.return_value = (True, None)
        resp = self.client.post(
            reverse("device_control_action"),
            data='{"entity_id": "switch.living_room_tv_socket_1", "action": "on", "type": "switch"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        mock_call.assert_called_once_with("switch", "turn_on", "switch.living_room_tv_socket_1", extra_data=None)

    def test_action_rejects_unknown_entity(self):
        resp = self.client.post(
            reverse("device_control_action"),
            data='{"entity_id": "switch.evil_entity", "action": "on", "type": "switch"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_action_rejects_bad_json(self):
        resp = self.client.post(
            reverse("device_control_action"),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_action_rejects_unknown_type(self):
        resp = self.client.post(
            reverse("device_control_action"),
            data='{"entity_id": "switch.living_room_tv_socket_1", "action": "on", "type": "thermostat"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    @patch("device_control.views.call_service")
    def test_action_cover_open(self, mock_call):
        mock_call.return_value = (True, None)
        resp = self.client.post(
            reverse("device_control_action"),
            data='{"entity_id": "cover.kitchen_left_window", "action": "open", "type": "cover"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_call.assert_called_once_with("cover", "open_cover", "cover.kitchen_left_window", extra_data=None)

    @patch("device_control.views.call_service")
    def test_action_ha_error_returns_502(self, mock_call):
        mock_call.return_value = (False, "HA timeout")
        resp = self.client.post(
            reverse("device_control_action"),
            data='{"entity_id": "switch.living_room_tv_socket_1", "action": "off", "type": "switch"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 502)
        data = resp.json()
        self.assertFalse(data["ok"])


@tag('selenium')
class DeviceControlShadesSliderTest(StaticLiveServerTestCase):
    """Ensure shade cards render a position slider that fits within the card."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from selenium import webdriver
        from tests.selenium_helpers import get_chrome_options
        cls.browser = webdriver.Chrome(options=get_chrome_options())
        cls.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
            'width': 1920,
            'height': 1080,
            'deviceScaleFactor': 1,
            'mobile': False,
        })

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def test_shade_slider_visible(self):
        """Each shade card must contain a visible position slider."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        self.browser.get(self.live_server_url + reverse("device_control"))

        # Click the Shades tab
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dc-tab"))
        )
        for tab_btn in self.browser.find_elements(By.CLASS_NAME, "dc-tab"):
            if "Shades" in tab_btn.text:
                tab_btn.click()
                break

        # Wait for shade cards to appear
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".dc-cover-slider"))
        )

        # Check every shade card's slider
        cards = self.browser.find_elements(By.CSS_SELECTOR, "[data-type='cover']")
        self.assertTrue(len(cards) > 0, "No shade cards found")

        for card in cards:
            card_rect = card.rect
            card_right = card_rect['x'] + card_rect['width']

            sliders = card.find_elements(By.CSS_SELECTOR, ".dc-cover-slider")
            self.assertEqual(len(sliders), 1,
                             f"Expected 1 slider in card, found {len(sliders)}")

            slider = sliders[0]
            slider_rect = slider.rect
            slider_right = slider_rect['x'] + slider_rect['width']

            # Slider must not extend beyond the card
            self.assertLessEqual(
                slider_right, card_right + 1,
                f"Slider right edge ({slider_right}px) extends "
                f"beyond card right edge ({card_right}px)"
            )

            # Slider must have positive visible dimensions
            self.assertGreater(
                slider_rect['width'], 0,
                "Slider has zero width — not visible"
            )
            self.assertGreater(
                slider_rect['height'], 0,
                "Slider has zero height — not visible"
            )
