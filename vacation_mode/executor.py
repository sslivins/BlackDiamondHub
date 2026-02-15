"""
Execution engine for vacation/home mode steps.

Runs steps sequentially in a background thread, calling the Home Assistant
REST API for each action. Supports retries and stores per-step status
in an in-memory store keyed by run_id.
"""

import threading
import time
import uuid
import requests
import logging
from urllib.parse import urljoin
from django.conf import settings

logger = logging.getLogger(__name__)

# In-memory store for run statuses: { run_id: { ... } }
_runs = {}

# Lock to prevent concurrent executions
_execution_lock = threading.Lock()

MAX_RETRIES = 2
RETRY_DELAY = 3  # seconds

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_RETRYING = "retrying"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"


def get_ha_headers():
    """Get authorization headers for Home Assistant API."""
    return {
        "Authorization": f"Bearer {settings.HOMEASSISTANT_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def get_ha_base_url():
    """Get the Home Assistant base URL."""
    return settings.HOMEASSISTANT_URL


def get_away_mode_state():
    """
    Query Home Assistant for the current state of input_boolean.home_away_mode_enabled.
    Returns True if away mode is on, False otherwise.
    """
    url = urljoin(get_ha_base_url(), "/api/states/input_boolean.home_away_mode_enabled")
    try:
        response = requests.get(url, headers=get_ha_headers(), timeout=10)
        if response.status_code == 200:
            state = response.json().get("state", "off")
            return state == "on"
    except requests.RequestException as e:
        logger.error(f"Failed to query away mode state: {e}")
    return False


def resolve_entity_id(device_id, domain, action_data):
    """
    Resolve entity_id for a device. For actions that target a device_id,
    we query HA's entity registry to find the matching entity.
    """
    # If entity_id is already provided in the action data, use it
    if action_data.get("entity_id"):
        return action_data["entity_id"]
    return None


def call_ha_service(action, data, device_id=None, area_id=None, entity_id_override=None, dry_run=False):
    """
    Call a Home Assistant service via the REST API.

    Args:
        action: Service to call in "domain/service" format (e.g. "climate/set_temperature")
        data: Payload dict
        device_id: Optional device_id (string or list) for targeting
        area_id: Optional area_id (string or list) for targeting
        entity_id_override: Optional entity_id to use instead of resolving from device
        dry_run: If True, simulate the call without hitting HA

    Returns:
        (success: bool, error_message: str or None)
    """
    domain, service = action.split("/")
    url = urljoin(get_ha_base_url(), f"/api/services/{domain}/{service}")

    payload = dict(data)

    # Build target - HA REST API accepts entity_id in the payload directly,
    # but for device_id/area_id targeting we need to structure it properly
    if entity_id_override:
        # Use the specific entity_id override
        payload["entity_id"] = entity_id_override
        # Remove None entity_id if present
        if "entity_id" in payload and payload["entity_id"] is None:
            payload["entity_id"] = entity_id_override
    elif device_id:
        # Remove None entity_id, use device targeting
        if "entity_id" in payload and payload["entity_id"] is None:
            del payload["entity_id"]
        if isinstance(device_id, list):
            payload["device_id"] = device_id
        else:
            payload["device_id"] = device_id
    elif area_id:
        if "entity_id" in payload and payload["entity_id"] is None:
            del payload["entity_id"]
        if isinstance(area_id, list):
            payload["area_id"] = area_id
        else:
            payload["area_id"] = area_id

    # Clean up None values
    payload = {k: v for k, v in payload.items() if v is not None}

    if dry_run:
        logger.info(f"[DRY RUN] Would call HA service: {url} with payload: {payload}")
        time.sleep(0.5)  # Simulate a short delay
        return True, None

    try:
        logger.info(f"Calling HA service: {url} with payload: {payload}")
        response = requests.post(url, headers=get_ha_headers(), json=payload, timeout=30)
        if response.status_code in (200, 201):
            return True, None
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            logger.error(f"HA service call failed: {error_msg}")
            return False, error_msg
    except requests.RequestException as e:
        error_msg = str(e)
        logger.error(f"HA service call exception: {error_msg}")
        return False, error_msg


def execute_step(step, step_status, dry_run=False):
    """
    Execute a single step (which may contain multiple actions).
    Updates step_status dict in-place.

    Returns True if the step succeeded, False otherwise.
    """
    actions = step.get("actions", [])
    sub_errors = []

    for i, action in enumerate(actions):
        success, error = call_ha_service(
            action=action["action"],
            data=action.get("data", {}),
            device_id=action.get("device_id"),
            area_id=action.get("area_id"),
            entity_id_override=action.get("entity_id_override"),
            dry_run=dry_run,
        )

        if not success:
            sub_errors.append(f"Action {i + 1} ({action['action']}): {error}")
            # Don't stop on sub-action failure within a step — try remaining actions
            continue

        # Apply delay if specified
        delay = action.get("delay_after", 0)
        if delay > 0:
            time.sleep(delay)

    if sub_errors:
        step_status["error"] = "; ".join(sub_errors)
        return False

    return True


def run_steps(run_id, steps, dry_run=False):
    """
    Execute all steps sequentially in a background thread.
    Updates _runs[run_id] with per-step status.
    """
    run_data = _runs[run_id]

    for idx, step in enumerate(steps):
        step_status = run_data["steps"][idx]
        step_status["status"] = STATUS_RUNNING
        step_status["attempt"] = 1

        success = execute_step(step, step_status, dry_run=dry_run)

        if not success:
            # Retry logic
            for retry in range(MAX_RETRIES):
                step_status["status"] = STATUS_RETRYING
                step_status["attempt"] = retry + 2
                step_status["error"] = None
                time.sleep(RETRY_DELAY)

                success = execute_step(step, step_status, dry_run=dry_run)
                if success:
                    break

        if success:
            step_status["status"] = STATUS_SUCCESS
            step_status["error"] = None
        else:
            step_status["status"] = STATUS_FAILED
            # error is already set by execute_step

    # Mark run as complete
    run_data["status"] = "complete"
    run_data["completed_at"] = time.time()

    # Release lock
    if _execution_lock.locked():
        _execution_lock.release()


def start_execution(mode, dry_run=False):
    """
    Start executing steps for the given mode.

    Args:
        mode: "vacation" or "home"
        dry_run: If True, simulate all steps without hitting HA

    Returns:
        (run_id, error_message) - error_message is None on success
    """
    from .steps import VACATION_STEPS, HOME_STEPS

    if not _execution_lock.acquire(blocking=False):
        return None, "An execution is already in progress"

    steps = VACATION_STEPS if mode == "vacation" else HOME_STEPS
    run_id = str(uuid.uuid4())[:8]

    _runs[run_id] = {
        "run_id": run_id,
        "mode": mode,
        "dry_run": dry_run,
        "status": "running",
        "started_at": time.time(),
        "completed_at": None,
        "steps": [
            {
                "alias": step["alias"],
                "icon": step["icon"],
                "status": STATUS_PENDING,
                "attempt": 0,
                "error": None,
            }
            for step in steps
        ],
    }

    thread = threading.Thread(target=run_steps, args=(run_id, steps, dry_run), daemon=True)
    thread.start()

    return run_id, None


def get_run_status(run_id):
    """Get the current status of a run."""
    return _runs.get(run_id)


def get_active_run():
    """Get the currently active (running) run, if any."""
    for run_id, run_data in _runs.items():
        if run_data["status"] == "running":
            return run_data
    return None
