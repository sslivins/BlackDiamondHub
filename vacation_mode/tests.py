from django.test import TestCase, Client
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from unittest.mock import patch, MagicMock
import json
import time
import unittest
import requests as requests_lib

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service as ChromeService

    # Try to use webdriver-manager for auto-matching chromedriver
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        _chrome_service = ChromeService(ChromeDriverManager().install())
    except ImportError:
        _chrome_service = None

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    _chrome_service = None

from .executor import (
    call_ha_service,
    execute_step,
    get_away_mode_state,
    start_execution,
    get_run_status,
    get_active_run,
    run_steps,
    _runs,
    _execution_lock,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_RETRYING,
    STATUS_SUCCESS,
    STATUS_FAILED,
    MAX_RETRIES,
    RETRY_DELAY,
)
from .steps import VACATION_STEPS, HOME_STEPS


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


class StepDefinitionTests(TestCase):
    """Tests to validate step definitions are well-formed."""

    def test_vacation_steps_not_empty(self):
        self.assertGreater(len(VACATION_STEPS), 0)

    def test_home_steps_not_empty(self):
        self.assertGreater(len(HOME_STEPS), 0)

    def test_all_vacation_steps_have_required_fields(self):
        for i, step in enumerate(VACATION_STEPS):
            with self.subTest(step=i, alias=step.get("alias")):
                self.assertIn("alias", step)
                self.assertIn("icon", step)
                self.assertIn("actions", step)
                self.assertIsInstance(step["actions"], list)
                self.assertGreater(len(step["actions"]), 0)

    def test_all_home_steps_have_required_fields(self):
        for i, step in enumerate(HOME_STEPS):
            with self.subTest(step=i, alias=step.get("alias")):
                self.assertIn("alias", step)
                self.assertIn("icon", step)
                self.assertIn("actions", step)
                self.assertIsInstance(step["actions"], list)
                self.assertGreater(len(step["actions"]), 0)

    def test_all_actions_have_action_field(self):
        """Every action must have a 'domain/service' format action field."""
        all_steps = VACATION_STEPS + HOME_STEPS
        for step in all_steps:
            for j, action in enumerate(step["actions"]):
                with self.subTest(step=step["alias"], action=j):
                    self.assertIn("action", action)
                    self.assertIn("/", action["action"], "Action must be 'domain/service' format")

    def test_all_actions_have_data(self):
        """Every action must have a data dict."""
        all_steps = VACATION_STEPS + HOME_STEPS
        for step in all_steps:
            for j, action in enumerate(step["actions"]):
                with self.subTest(step=step["alias"], action=j):
                    self.assertIn("data", action)
                    self.assertIsInstance(action["data"], dict)

    def test_all_actions_have_targeting(self):
        """Every action must have at least one targeting method."""
        all_steps = VACATION_STEPS + HOME_STEPS
        for step in all_steps:
            for j, action in enumerate(step["actions"]):
                with self.subTest(step=step["alias"], action=j):
                    has_entity = action["data"].get("entity_id") is not None
                    has_device = action.get("device_id") is not None
                    has_area = action.get("area_id") is not None
                    has_override = action.get("entity_id_override") is not None
                    self.assertTrue(
                        has_entity or has_device or has_area or has_override,
                        f"Action has no targeting (entity_id, device_id, area_id, or entity_id_override)"
                    )

    def test_icons_are_font_awesome(self):
        """All step icons should be Font Awesome classes."""
        all_steps = VACATION_STEPS + HOME_STEPS
        for step in all_steps:
            with self.subTest(step=step["alias"]):
                self.assertTrue(
                    step["icon"].startswith("fas ") or step["icon"].startswith("fab "),
                    f"Icon '{step['icon']}' doesn't look like a Font Awesome class"
                )


class RunStepsTests(TestCase):
    """Tests for the full run_steps execution flow."""

    def setUp(self):
        # Ensure lock is released before each test
        if _execution_lock.locked():
            _execution_lock.release()

    def tearDown(self):
        # Clean up
        if _execution_lock.locked():
            _execution_lock.release()
        _runs.clear()

    @patch("vacation_mode.executor.call_ha_service")
    def test_all_steps_succeed(self, mock_call):
        mock_call.return_value = (True, None)

        steps = [
            {"alias": "Step 1", "icon": "fas fa-test", "actions": [{"action": "switch/turn_on", "data": {"entity_id": "s1"}}]},
            {"alias": "Step 2", "icon": "fas fa-test", "actions": [{"action": "switch/turn_on", "data": {"entity_id": "s2"}}]},
        ]

        run_id = "test-run-1"
        _execution_lock.acquire()
        _runs[run_id] = {
            "run_id": run_id, "mode": "vacation", "status": "running",
            "steps": [{"alias": s["alias"], "icon": s["icon"], "status": STATUS_PENDING, "attempt": 0, "error": None} for s in steps],
        }

        run_steps(run_id, steps)

        run_data = _runs[run_id]
        self.assertEqual(run_data["status"], "complete")
        for step in run_data["steps"]:
            self.assertEqual(step["status"], STATUS_SUCCESS)

    @patch("vacation_mode.executor.call_ha_service")
    @patch("vacation_mode.executor.RETRY_DELAY", 0)
    def test_step_retries_then_succeeds(self, mock_call):
        """A step that fails once then succeeds on retry."""
        mock_call.side_effect = [(False, "timeout"), (True, None)]

        steps = [
            {"alias": "Flaky Step", "icon": "fas fa-test", "actions": [{"action": "switch/turn_on", "data": {"entity_id": "s1"}}]},
        ]

        run_id = "test-run-2"
        _execution_lock.acquire()
        _runs[run_id] = {
            "run_id": run_id, "mode": "vacation", "status": "running",
            "steps": [{"alias": "Flaky Step", "icon": "fas fa-test", "status": STATUS_PENDING, "attempt": 0, "error": None}],
        }

        run_steps(run_id, steps)

        run_data = _runs[run_id]
        self.assertEqual(run_data["steps"][0]["status"], STATUS_SUCCESS)
        self.assertEqual(run_data["status"], "complete")

    @patch("vacation_mode.executor.call_ha_service")
    @patch("vacation_mode.executor.RETRY_DELAY", 0)
    def test_step_fails_all_retries_then_continues(self, mock_call):
        """A step that fails all retries — the run should still complete (continue past it)."""
        # First step always fails, second step succeeds
        mock_call.side_effect = [
            (False, "error")] * (1 + MAX_RETRIES) + [(True, None)
        ]

        steps = [
            {"alias": "Bad Step", "icon": "fas fa-test", "actions": [{"action": "switch/turn_on", "data": {"entity_id": "s1"}}]},
            {"alias": "Good Step", "icon": "fas fa-test", "actions": [{"action": "switch/turn_on", "data": {"entity_id": "s2"}}]},
        ]

        run_id = "test-run-3"
        _execution_lock.acquire()
        _runs[run_id] = {
            "run_id": run_id, "mode": "vacation", "status": "running",
            "steps": [
                {"alias": "Bad Step", "icon": "fas fa-test", "status": STATUS_PENDING, "attempt": 0, "error": None},
                {"alias": "Good Step", "icon": "fas fa-test", "status": STATUS_PENDING, "attempt": 0, "error": None},
            ],
        }

        run_steps(run_id, steps)

        run_data = _runs[run_id]
        self.assertEqual(run_data["status"], "complete")
        self.assertEqual(run_data["steps"][0]["status"], STATUS_FAILED)
        self.assertEqual(run_data["steps"][1]["status"], STATUS_SUCCESS)

    @patch("vacation_mode.executor.call_ha_service")
    def test_run_releases_lock_on_completion(self, mock_call):
        mock_call.return_value = (True, None)
        steps = [{"alias": "S", "icon": "fas fa-test", "actions": [{"action": "switch/turn_on", "data": {"entity_id": "s1"}}]}]

        run_id = "test-run-4"
        _execution_lock.acquire()
        _runs[run_id] = {
            "run_id": run_id, "mode": "vacation", "status": "running",
            "steps": [{"alias": "S", "icon": "fas fa-test", "status": STATUS_PENDING, "attempt": 0, "error": None}],
        }

        run_steps(run_id, steps)
        # Lock should be released — we can acquire it again
        acquired = _execution_lock.acquire(blocking=False)
        self.assertTrue(acquired)
        if acquired:
            _execution_lock.release()


class StartExecutionTests(TestCase):
    """Tests for the start_execution function."""

    def setUp(self):
        if _execution_lock.locked():
            _execution_lock.release()
        _runs.clear()

    def tearDown(self):
        # Wait for any background threads to finish
        time.sleep(0.2)
        if _execution_lock.locked():
            _execution_lock.release()
        _runs.clear()

    @patch("vacation_mode.executor.call_ha_service")
    def test_start_vacation_mode(self, mock_call):
        mock_call.return_value = (True, None)
        run_id, error = start_execution("vacation", dry_run=True)
        self.assertIsNotNone(run_id)
        self.assertIsNone(error)

    @patch("vacation_mode.executor.call_ha_service")
    def test_start_home_mode(self, mock_call):
        mock_call.return_value = (True, None)
        run_id, error = start_execution("home", dry_run=True)
        self.assertIsNotNone(run_id)
        self.assertIsNone(error)

    @patch("vacation_mode.executor.call_ha_service")
    def test_concurrent_execution_blocked(self, mock_call):
        """Cannot start a second execution while one is running."""
        # Simulate a long-running step
        def slow_call(*args, **kwargs):
            time.sleep(2)
            return True, None
        mock_call.side_effect = slow_call

        run_id1, error1 = start_execution("vacation", dry_run=True)
        self.assertIsNotNone(run_id1)
        self.assertIsNone(error1)

        # Try to start another — should fail
        run_id2, error2 = start_execution("home", dry_run=True)
        self.assertIsNone(run_id2)
        self.assertIn("already in progress", error2)

    @patch("vacation_mode.executor.call_ha_service")
    def test_run_stores_dry_run_flag(self, mock_call):
        mock_call.return_value = (True, None)
        run_id, _ = start_execution("vacation", dry_run=True)
        self.assertTrue(_runs[run_id]["dry_run"])

    @patch("vacation_mode.executor.call_ha_service")
    def test_run_status_has_all_steps(self, mock_call):
        mock_call.return_value = (True, None)
        run_id, _ = start_execution("vacation", dry_run=True)
        status = get_run_status(run_id)
        self.assertIsNotNone(status)
        self.assertEqual(len(status["steps"]), len(VACATION_STEPS))


class AdditionalViewTests(TestCase):
    """Additional view tests for edge cases."""

    def setUp(self):
        self.client = Client()

    def test_execute_get_not_allowed(self):
        """Execute endpoint should reject GET requests."""
        response = self.client.get("/vacation_mode/api/execute/")
        self.assertEqual(response.status_code, 405)

    def test_execute_empty_body(self):
        """Execute with empty body should return 400."""
        response = self.client.post(
            "/vacation_mode/api/execute/",
            data="",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_execute_no_mode(self):
        """Execute without mode field should return 400."""
        response = self.client.post(
            "/vacation_mode/api/execute/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_status_post_not_allowed(self):
        """Status endpoint should reject POST requests."""
        response = self.client.post("/vacation_mode/api/status/test/")
        self.assertEqual(response.status_code, 405)

    def test_state_post_not_allowed(self):
        """State endpoint should reject POST requests."""
        response = self.client.post("/vacation_mode/api/state/")
        self.assertEqual(response.status_code, 405)

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_main_page_vacation_mode_context(self, mock_active, mock_away):
        """When home, mode should be vacation (button to leave)."""
        mock_away.return_value = False
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        self.assertEqual(response.context["mode"], "vacation")
        self.assertFalse(response.context["is_away"])

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_main_page_home_mode_context(self, mock_active, mock_away):
        """When away, mode should be home (button to arrive)."""
        mock_away.return_value = True
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        self.assertEqual(response.context["mode"], "home")
        self.assertTrue(response.context["is_away"])

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_main_page_contains_step_json(self, mock_active, mock_away):
        """The page should contain JSON step data."""
        mock_away.return_value = False
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        content = response.content.decode()
        # Steps JSON should be embedded in the page
        self.assertIn("pending", content)

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_main_page_shows_vacation_button_when_home(self, mock_active, mock_away):
        mock_away.return_value = False
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        self.assertContains(response, "Set Vacation Mode")

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_main_page_shows_arrival_button_when_away(self, mock_active, mock_away):
        mock_away.return_value = True
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        self.assertContains(response, "Prepare for Arrival")

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_dry_run_checkbox_unchecked_by_default(self, mock_active, mock_away):
        """Dry run checkbox should be unchecked by default."""
        mock_away.return_value = False
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        content = response.content.decode()
        self.assertNotIn('checked', content.split('dry-run-checkbox')[1].split('>')[0])
        self.assertIn('let dryRun = false', content)

    @patch("vacation_mode.views.start_execution")
    def test_execute_dry_run_false_by_default(self, mock_start):
        """Without dry_run in body, it should default to False."""
        mock_start.return_value = ("abc123", None)
        self.client.post(
            "/vacation_mode/api/execute/",
            data=json.dumps({"mode": "vacation"}),
            content_type="application/json",
        )
        mock_start.assert_called_once_with("vacation", dry_run=False)


class TemplateRenderTests(TestCase):
    """Tests for template rendering correctness."""

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_template_has_step_list(self, mock_active, mock_away):
        mock_away.return_value = False
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        self.assertContains(response, 'id="step-list"')

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_template_has_progress_bar(self, mock_active, mock_away):
        mock_away.return_value = False
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        self.assertContains(response, 'id="progress-container"')
        self.assertContains(response, 'id="progress-bar"')

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_template_has_status_badge(self, mock_active, mock_away):
        mock_away.return_value = False
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        self.assertContains(response, 'id="status-badge"')

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_away_badge_class(self, mock_active, mock_away):
        mock_away.return_value = True
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        self.assertContains(response, "status-badge away")

    @patch("vacation_mode.views.get_away_mode_state")
    @patch("vacation_mode.views.get_active_run")
    def test_home_badge_class(self, mock_active, mock_away):
        mock_away.return_value = False
        mock_active.return_value = None
        response = self.client.get("/vacation_mode/")
        self.assertContains(response, "status-badge home")

    def setUp(self):
        self.client = Client()


class HomepageIconTests(TestCase):
    """Tests for the vacation mode icon on the homepage."""

    def setUp(self):
        self.client = Client()

    @patch("BlackDiamondHub.views.requests.get")
    def test_homepage_has_vacation_link(self, mock_get):
        mock_response = MagicMock(status_code=200)
        mock_response.content = b'<div class="weather current-conditions"><ul class="list-temps"></ul></div>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        response = self.client.get("/")
        self.assertContains(response, "/vacation_mode/")

    @patch("BlackDiamondHub.views.requests.get")
    def test_homepage_has_vacation_icon(self, mock_get):
        mock_response = MagicMock(status_code=200)
        mock_response.content = b'<div class="weather current-conditions"><ul class="list-temps"></ul></div>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        response = self.client.get("/")
        self.assertContains(response, "vacation.png")

    @patch("BlackDiamondHub.views.requests.get")
    def test_homepage_has_vacation_caption(self, mock_get):
        mock_response = MagicMock(status_code=200)
        mock_response.content = b'<div class="weather current-conditions"><ul class="list-temps"></ul></div>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        response = self.client.get("/")
        self.assertContains(response, "Vacation Mode")


class SeleniumVacationModeTests(StaticLiveServerTestCase):
    """Selenium tests to validate the vacation mode page renders correctly at 1920x1080."""

    _original_get_away_mode_state = None

    @classmethod
    def setUpClass(cls):
        if not SELENIUM_AVAILABLE:
            raise unittest.SkipTest("Selenium not available")
        super().setUpClass()
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        try:
            if _chrome_service:
                cls.driver = webdriver.Chrome(service=_chrome_service, options=chrome_options)
            else:
                cls.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            raise unittest.SkipTest(f"Chrome WebDriver not available: {e}")
        cls.driver.set_window_size(1920, 1080)
        cls.driver.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        # Monkeypatch get_away_mode_state so the live server uses our mock
        from vacation_mode import views as vm_views
        self._original_get_away_mode_state = vm_views.get_away_mode_state
        vm_views.get_away_mode_state = lambda: False

    def tearDown(self):
        from vacation_mode import views as vm_views
        vm_views.get_away_mode_state = self._original_get_away_mode_state

    def _set_away_state(self, is_away):
        from vacation_mode import views as vm_views
        vm_views.get_away_mode_state = lambda: is_away

    def test_no_vertical_scrollbar_at_1080p(self):
        """Page should fit within 1920x1080 without vertical scrollbar."""
        self.driver.get(f"{self.live_server_url}/vacation_mode/")
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, "step-list"))
        )
        scroll_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        client_height = self.driver.execute_script("return document.documentElement.clientHeight")
        self.assertLessEqual(
            scroll_height, client_height,
            f"Page has vertical scrollbar: scrollHeight={scroll_height} > clientHeight={client_height}"
        )

    def test_no_horizontal_scrollbar_at_1080p(self):
        """Page should fit within 1920x1080 without horizontal scrollbar."""
        self.driver.get(f"{self.live_server_url}/vacation_mode/")
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, "step-list"))
        )
        scroll_width = self.driver.execute_script("return document.documentElement.scrollWidth")
        client_width = self.driver.execute_script("return document.documentElement.clientWidth")
        self.assertLessEqual(
            scroll_width, client_width,
            f"Page has horizontal scrollbar: scrollWidth={scroll_width} > clientWidth={client_width}"
        )

    def test_step_items_render_on_page(self):
        """Step items should be rendered on the page."""
        self.driver.get(f"{self.live_server_url}/vacation_mode/")
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, "step-list"))
        )
        step_items = self.driver.find_elements(By.CSS_SELECTOR, ".step-item")
        self.assertEqual(len(step_items), len(VACATION_STEPS))

    def test_home_steps_render_when_away(self):
        """When away, home steps should be shown."""
        self._set_away_state(True)
        self.driver.get(f"{self.live_server_url}/vacation_mode/")
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, "step-list"))
        )
        step_items = self.driver.find_elements(By.CSS_SELECTOR, ".step-item")
        self.assertEqual(len(step_items), len(HOME_STEPS))

    def test_step_items_are_single_line(self):
        """Each step item should be a single-line row (no wrapping)."""
        self.driver.get(f"{self.live_server_url}/vacation_mode/")
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, "step-list"))
        )
        step_items = self.driver.find_elements(By.CSS_SELECTOR, ".step-item")
        for item in step_items:
            height = item.size["height"]
            # A single-line row with padding should be under 65px
            self.assertLessEqual(height, 65, f"Step item too tall ({height}px), may be wrapping")

    def test_action_button_visible(self):
        """The action button should be visible."""
        self.driver.get(f"{self.live_server_url}/vacation_mode/")
        btn = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, "action-btn"))
        )
        self.assertTrue(btn.is_displayed())
        self.assertIn("Set Vacation Mode", btn.text)

    def test_action_button_shows_arrival_when_away(self):
        """When away, button should show Prepare for Arrival."""
        self._set_away_state(True)
        self.driver.get(f"{self.live_server_url}/vacation_mode/")
        btn = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, "action-btn"))
        )
        self.assertIn("Prepare for Arrival", btn.text)

    def test_dry_run_unchecked_by_default(self):
        """Dry run checkbox should be unchecked by default."""
        self.driver.get(f"{self.live_server_url}/vacation_mode/")
        checkbox = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, "dry-run-checkbox"))
        )
        self.assertFalse(checkbox.is_selected())
