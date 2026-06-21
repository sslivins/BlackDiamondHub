"""
Async bridge between sync Django and the async ``pygemstone`` cloud client.

``pygemstone`` talks to the Gemstone Lights (AWS Amplify / Cognito) cloud over
aiohttp and is entirely ``async``. Django's request handling here is synchronous
(WSGI), so we cannot simply ``asyncio.run()`` a fresh coroutine per request: the
logged-in ``GemstoneClient`` owns an aiohttp ``ClientSession`` bound to the event
loop it was created on, and re-using it from a different loop raises
``RuntimeError: ... attached to a different loop``.

The robust pattern (identical to ``napoleon_client``) is a single **dedicated
background event loop** running in its own daemon thread for the lifetime of the
process. The cached client + session + device handles live on that loop forever;
sync callers submit coroutines to it via ``asyncio.run_coroutine_threadsafe`` and
block on the result.

Public sync API:
    * :func:`get_states`  -> dict  {"devices": [...], "patterns": [...]}
    * :func:`apply_action(device_id, action, value)` -> dict (refreshed state)
    * :func:`is_configured` -> bool

All cloud/network errors are surfaced as :class:`GemstoneError` so the views can
turn them into clean JSON responses.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable, Coroutine

from django.conf import settings

logger = logging.getLogger(__name__)

# How long a sync caller will block on a coroutine submitted to the loop.
_CALL_TIMEOUT = 25  # seconds

# How many pages of saved patterns to pull when discovering the catalogue.
_MAX_PATTERN_PAGES = 5


class GemstoneError(Exception):
    """Any failure talking to the Gemstone cloud (auth, network, value)."""


# ---------------------------------------------------------------------------
# Dedicated background event-loop thread
# ---------------------------------------------------------------------------
class _LoopThread:
    """Owns a single asyncio loop running in a daemon thread."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run, name="gemstone-loop", daemon=True
        )
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro: Coroutine[Any, Any, Any], timeout: int = _CALL_TIMEOUT) -> Any:
        """Submit ``coro`` to the loop and block until it returns."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=timeout)
        except asyncio.TimeoutError as exc:  # pragma: no cover - network timing
            future.cancel()
            raise GemstoneError("Gemstone cloud request timed out") from exc


# Lazily created so importing this module (e.g. during `manage.py check`) never
# spins up a thread.
_loop_thread: _LoopThread | None = None
_loop_lock = threading.Lock()


def _loop() -> _LoopThread:
    global _loop_thread
    if _loop_thread is None:
        with _loop_lock:
            if _loop_thread is None:
                _loop_thread = _LoopThread()
    return _loop_thread


# ---------------------------------------------------------------------------
# Cached client + handles (all live on the loop thread)
# ---------------------------------------------------------------------------
# These are only ever touched from coroutines running on the loop thread, so no
# additional locking is required around them.
_client: Any = None  # GemstoneClient
_devices: dict[str, Any] = {}  # device_id -> Device
_patterns_by_id: dict[str, Any] = {}  # pattern_id -> Pattern (for replay)
_patterns_ui: list[dict[str, Any]] = []  # JSON-friendly catalogue for the UI


def is_configured() -> bool:
    """True when Gemstone cloud credentials are present in settings."""
    return bool(
        getattr(settings, "GEMSTONE_EMAIL", "")
        and getattr(settings, "GEMSTONE_PASSWORD", "")
    )


def _color_to_hex(c: Any) -> str:
    """Best-effort conversion of a packed integer colour to ``#rrggbb``."""
    try:
        n = int(c)
    except (TypeError, ValueError):
        return "#000000"
    return "#%06x" % (n & 0xFFFFFF)


async def _ensure_client() -> None:
    """Log in and discover devices + saved patterns if we have no live client."""
    global _client, _devices, _patterns_by_id, _patterns_ui
    if _client is not None and _devices:
        return

    # Imported lazily so the app loads even if pygemstone is missing.
    from pygemstone import GemstoneClient
    from pygemstone.errors import GemstoneError as LibGemstoneError

    email = getattr(settings, "GEMSTONE_EMAIL", "")
    password = getattr(settings, "GEMSTONE_PASSWORD", "")
    if not (email and password):
        raise GemstoneError("Gemstone credentials are not configured")

    client = GemstoneClient(email, password)
    try:
        # __aenter__ creates the aiohttp session on THIS loop; we drive the
        # context manager manually because the client is cached for the
        # process lifetime rather than scoped to a single ``async with``.
        await client.__aenter__()
        await client.login()
        devices = await client.devices()
        patterns = await _discover_patterns(client)
    except LibGemstoneError as exc:
        await _safe_close(client)
        raise GemstoneError(f"Gemstone login/discovery failed: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - surface any startup failure cleanly
        await _safe_close(client)
        raise GemstoneError(f"Gemstone login/discovery failed: {exc}") from exc

    _client = client
    _devices = {d.id: d for d in devices}

    by_id: dict[str, Any] = {}
    ui: list[dict[str, Any]] = []
    for fp in patterns:
        pat = fp.pattern
        pid = getattr(pat, "id", "") or ""
        if not pid or pid in by_id:
            continue
        by_id[pid] = pat
        ui.append(
            {
                "id": pid,
                "name": pat.name or "Pattern",
                "colors": [_color_to_hex(c) for c in (pat.colors or [])],
                "is_favorite": bool(getattr(fp, "is_favorite", False)),
            }
        )
    # Favourites first, then alphabetical — stable, friendly ordering.
    ui.sort(key=lambda p: (not p["is_favorite"], p["name"].lower()))
    _patterns_by_id = by_id
    _patterns_ui = ui
    logger.info(
        "Gemstone: discovered %d device(s), %d saved pattern(s)",
        len(_devices),
        len(_patterns_ui),
    )


async def _discover_patterns(client: Any) -> list[Any]:
    """Pull the user's saved patterns across a bounded number of pages."""
    out: list[Any] = []
    for page in range(1, _MAX_PATTERN_PAGES + 1):
        chunk = await client.folder_patterns(page=page)
        if not chunk:
            break
        out.extend(chunk)
    return out


async def _safe_close(client: Any) -> None:
    try:
        await client.__aexit__(None, None, None)
    except Exception:  # pragma: no cover - best-effort cleanup
        pass


async def _reset() -> None:
    """Drop the cached client (forces a fresh login on the next call)."""
    global _client, _devices, _patterns_by_id, _patterns_ui
    client, _client = _client, None
    _devices = {}
    _patterns_by_id = {}
    _patterns_ui = []
    if client is not None:
        await _safe_close(client)


def _state_to_dict(dev: Any) -> dict[str, Any]:
    """Serialize a Device's cached state into a JSON-friendly dict."""
    s = dev.state  # DeviceState | None
    pattern = getattr(s, "pattern", None) if s is not None else None
    return {
        "id": dev.id,
        "name": dev.name,
        "online": not bool(getattr(dev.record, "disconnect_reason", None)),
        "power": bool(getattr(s, "on_state", False)) if s is not None else False,
        "pattern_id": getattr(pattern, "id", None) if pattern else None,
        "pattern_name": getattr(pattern, "name", None) if pattern else None,
        "pattern_colors": (
            [_color_to_hex(c) for c in (pattern.colors or [])] if pattern else []
        ),
    }


# ---------------------------------------------------------------------------
# Coroutines (run on the loop thread)
# ---------------------------------------------------------------------------
async def _get_states() -> dict[str, Any]:
    await _ensure_client()
    devs = list(_devices.values())
    # Refresh all devices concurrently.
    await asyncio.gather(*(dev.refresh() for dev in devs))
    return {
        "devices": [_state_to_dict(dev) for dev in devs],
        "patterns": list(_patterns_ui),
    }


async def _set_power(dev: Any, value: Any) -> None:
    if bool(value):
        await dev.turn_on()
    else:
        await dev.turn_off()


async def _play_pattern(dev: Any, value: Any) -> None:
    pattern = _patterns_by_id.get(str(value))
    if pattern is None:
        raise GemstoneError(f"Unknown pattern: {value}")
    await dev.play_pattern(pattern)


# action name -> coroutine factory taking (device, value)
_ACTIONS: dict[str, Callable[[Any, Any], Coroutine[Any, Any, None]]] = {
    "power": _set_power,
    "pattern": _play_pattern,
}


async def _apply_action(device_id: str, action: str, value: Any) -> dict[str, Any]:
    from pygemstone.errors import GemstoneError as LibGemstoneError

    await _ensure_client()
    dev = _devices.get(device_id)
    if dev is None:
        raise GemstoneError(f"Unknown device: {device_id}")

    handler = _ACTIONS.get(action)
    if handler is None:
        raise GemstoneError(f"Unknown action: {action}")

    try:
        await handler(dev, value)
        # Reflect the change back to the caller.
        await dev.refresh()
    except LibGemstoneError as exc:
        raise GemstoneError(f"{action} failed: {exc}") from exc
    return _state_to_dict(dev)


# ---------------------------------------------------------------------------
# Public sync API (called from Django views) — with one auth/connection retry
# ---------------------------------------------------------------------------
def _run_with_retry(make_coro: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
    """Run a coroutine on the loop, retrying once after a fresh login.

    A cached client whose token/session has gone stale (process idle, cloud-side
    session reaped, etc.) surfaces as a GemstoneError. We drop the cache,
    re-login, and retry exactly once before giving up.
    """
    loop = _loop()
    try:
        return loop.run(make_coro())
    except GemstoneError:
        logger.warning("Gemstone call failed; resetting client and retrying once")
        loop.run(_reset())
        return loop.run(make_coro())


def get_states() -> dict[str, Any]:
    """Return current device states plus the saved-pattern catalogue."""
    return _run_with_retry(_get_states)


def apply_action(device_id: str, action: str, value: Any) -> dict[str, Any]:
    """Apply a single control action and return the refreshed device state."""
    return _run_with_retry(lambda: _apply_action(device_id, action, value))
