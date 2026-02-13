from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
import json
import requests as requests_lib

from .executor import (
    call_ha_service,
    execute_step,
    get_away_mode_state,
    start_execution,
    get_run_status,
    _runs,
    _execution_lock,
    STATUS_PENDING,
    STATUS_SUCCESS,
    STATUS_FAILED,
)


class GetAwayModeStateTests(TestCase):
    """Tests for querying the away mode state from Home Assistant."""

    @patch("vacation_mode.executor.requests.get")
    def test_returns_true_when_on(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"state": "on", "entity_id": "input_boolean.home_away_mode_enabled"},
        )
        self.assertTrue(get_away_mode_state())

    @patch("vacation_mode.executor.requests.get")
    def test_returns_false_when_off(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"state": "off", "entity_id": "input_boolean.home_away_mode_enabled"},
        )
        self.assertFalse(get_away_mode_state())

    @patch("vacation_mode.executor.requests.get")
    def test_returns_false_on_error(self, mock_get):
        mock_get.side_effect = requests_lib.RequestException("Connection refused")
        self.assertFalse(get_away_mode_state())


class CallHaServiceTests(TestCase):
    """Tests for calling Home Assistant services."""

    @patch("vacation_mode.executor.requests.post")
    def test_successful_call(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        success, error = call_ha_service(
            action="input_boolean/turn_on",
            data={"entity_id": "input_boolean.home_away_mode_enabled"},
        )
        self.assertTrue(success)
        self.assertIsNone(error)

    @patch("vacation_mode.executor.requests.post")
    def test_failed_call_returns_error(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500, text="Internal Server Error")
        success, error = call_ha_service(
            action="climate/set_temperature",
            data={"temperature": 13.5},
            device_id="abc123",
        )
        self.assertFalse(success)
        self.assertIn("500", error)

    @patch("vacation_mode.executor.requests.post")
    def test_network_exception(self, mock_post):
        mock_post.side_effect = requests_lib.ConnectionError("Connection timeout")
        success, error = call_ha_service(
            action="switch/turn_on",
            data={"entity_id": "switch.test"},
        )
        self.assertFalse(success)
        self.assertIn("Connection timeout", error)

    @patch("vacation_mode.executor.requests.post")
    def test_device_id_targeting(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        call_ha_service(
            action="climate/set_temperature",
            data={"entity_id": None, "temperature": 20},
            device_id="test_device",
        )
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertEqual(payload["device_id"], "test_device")
        self.assertNotIn("entity_id", payload)

    @patch("vacation_mode.executor.requests.post")
    def test_area_id_targeting(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        call_ha_service(
            action="climate/set_temperature",
            data={"temperature": 5},
            area_id=["garage", "garage_storage_room"],
        )
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertEqual(payload["area_id"], ["garage", "garage_storage_room"])

    @patch("vacation_mode.executor.requests.post")
    def test_entity_id_override(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        call_ha_service(
            action="switch/turn_on",
            data={"entity_id": None},
            device_id="some_device",
            entity_id_override="switch.specific_entity",
        )
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertEqual(payload["entity_id"], "switch.specific_entity")


class ExecuteStepTests(TestCase):
    """Tests for executing individual steps."""

    @patch("vacation_mode.executor.call_ha_service")
    def test_step_success(self, mock_call):
        mock_call.return_value = (True, None)
        step = {
            "alias": "Test Step",
            "actions": [
                {"action": "switch/turn_on", "data": {"entity_id": "switch.test"}},
            ],
        }
        step_status = {"status": "running", "error": None}
        result = execute_step(step, step_status)
        self.assertTrue(result)

    @patch("vacation_mode.executor.call_ha_service")
    def test_step_failure(self, mock_call):
        mock_call.return_value = (False, "Service unavailable")
        step = {
            "alias": "Test Step",
            "actions": [
                {"action": "switch/turn_on", "data": {"entity_id": "switch.test"}},
            ],
        }
        step_status = {"status": "running", "error": None}
        result = execute_step(step, step_status)
        self.assertFalse(result)
        self.assertIn("Service unavailable", step_status["error"])

    @patch("vacation_mode.executor.call_ha_service")
    def test_partial_action_failure(self, mock_call):
        """If one action in a step fails but others succeed, the step still fails."""
        mock_call.side_effect = [(True, None), (False, "Error"), (True, None)]
        step = {
            "alias": "Multi-action Step",
            "actions": [
                {"action": "switch/turn_on", "data": {"entity_id": "s1"}},
                {"action": "switch/turn_on", "data": {"entity_id": "s2"}},
                {"action": "switch/turn_on", "data": {"entity_id": "s3"}},
            ],
        }
        step_status = {"status": "running", "error": None}
        result = execute_step(step, step_status)
        self.assertFalse(result)
        # But all 3 actions were attempted (continue on sub-action failure)
        self.assertEqual(mock_call.call_count, 3)


class ViewTests(TestCase):
    """Tests for the vacation mode views."""

    def setUp(self):
        self.client = Client()

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_main_page_loads(self, mock_active, mock_away):
        mock_away.return_value = False
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vacation Mode")

    @patch("vacation_mode.views.start_execution")
    def test_execute_returns_run_id(self, mock_start):
        mock_start.return_value = ("abc123", None)
        response = self.client.post(
            "/vacation_mode/api/execute/",
            data=json.dumps({"mode": "vacation"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["run_id"], "abc123")

    def test_execute_invalid_mode(self):
        response = self.client.post(
            "/vacation_mode/api/execute/",
            data=json.dumps({"mode": "invalid"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("vacation_mode.views.start_execution")
    def test_execute_already_running(self, mock_start):
        mock_start.return_value = (None, "An execution is already in progress")
        response = self.client.post(
            "/vacation_mode/api/execute/",
            data=json.dumps({"mode": "vacation"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)

    def test_status_not_found(self):
        response = self.client.get("/vacation_mode/api/status/nonexistent/")
        self.assertEqual(response.status_code, 404)

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_state_endpoint(self, mock_active, mock_away):
        mock_away.return_value = True
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/api/state/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_away"])
        self.assertIsNone(data["active_run"])


class DryRunTests(TestCase):
    """Tests for dry run mode."""

    @patch("vacation_mode.executor.requests.post")
    def test_dry_run_skips_api_call(self, mock_post):
        """Dry run should not make any HTTP requests."""
        success, error = call_ha_service(
            action="switch/turn_on",
            data={"entity_id": "switch.test"},
            dry_run=True,
        )
        self.assertTrue(success)
        self.assertIsNone(error)
        mock_post.assert_not_called()

    @patch("vacation_mode.executor.requests.post")
    def test_dry_run_execute_step(self, mock_post):
        """Dry run step should succeed without HTTP calls."""
        step = {
            "alias": "Test Step",
            "actions": [
                {"action": "switch/turn_on", "data": {"entity_id": "switch.test"}},
                {"action": "switch/turn_off", "data": {"entity_id": "switch.test2"}},
            ],
        }
        step_status = {"status": "running", "error": None}
        result = execute_step(step, step_status, dry_run=True)
        self.assertTrue(result)
        mock_post.assert_not_called()

    @patch("vacation_mode.views.start_execution")
    def test_execute_passes_dry_run(self, mock_start):
        """Execute view should pass dry_run to start_execution."""
        mock_start.return_value = ("abc123", None)
        client = Client()
        response = client.post(
            "/vacation_mode/api/execute/",
            data=json.dumps({"mode": "vacation", "dry_run": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_start.assert_called_once_with("vacation", dry_run=True)
