"""
Async bridge between sync Django and the async ``pynapoleon`` cloud client.

``pynapoleon`` talks to the Napoleon (Ayla) cloud over aiohttp and is entirely
``async``. Django's request handling here is synchronous (WSGI), so we cannot
simply ``asyncio.run()`` a fresh coroutine per request: the logged-in
``NapoleonClient`` owns an aiohttp ``ClientSession`` that is bound to the event
loop it was created on, and re-using it from a different loop raises
``RuntimeError: ... attached to a different loop``.

The robust pattern is a single **dedicated background event loop** running in
its own daemon thread for the lifetime of the process. The cached client and
its session live on that loop forever; sync callers submit coroutines to it via
``asyncio.run_coroutine_threadsafe`` and block on the result.

Public sync API:
    * :func:`get_states`  -> list[dict]   (one per discovered fireplace)
    * :func:`apply_action(dsn, action, value)` -> dict (the refreshed state)
    * :func:`is_configured` -> bool

All Ayla/network errors are surfaced as :class:`FireplaceError` so the views can
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


class FireplaceError(Exception):
    """Any failure talking to the Napoleon cloud (auth, network, value)."""


# ---------------------------------------------------------------------------
# Dedicated background event-loop thread
# ---------------------------------------------------------------------------
class _LoopThread:
    """Owns a single asyncio loop running in a daemon thread."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run, name="napoleon-loop", daemon=True
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
            raise FireplaceError("Napoleon cloud request timed out") from exc


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
# Cached client + fireplace handles (all live on the loop thread)
# ---------------------------------------------------------------------------
# These are only ever touched from coroutines running on the loop thread, so no
# additional locking is required around them.
_client: Any = None  # NapoleonClient
_fireplaces: dict[str, Any] = {}  # dsn -> Fireplace


def is_configured() -> bool:
    """True when Napoleon cloud credentials are present in settings."""
    return bool(
        getattr(settings, "NAPOLEON_EMAIL", "")
        and getattr(settings, "NAPOLEON_PASSWORD", "")
    )


async def _ensure_client() -> None:
    """Log in and discover fireplaces if we don't have a live client yet."""
    global _client, _fireplaces
    if _client is not None and _fireplaces:
        return

    # Imported lazily so the app loads even if pynapoleon is missing.
    from pynapoleon import NapoleonClient
    from pynapoleon.errors import NapoleonError

    email = getattr(settings, "NAPOLEON_EMAIL", "")
    password = getattr(settings, "NAPOLEON_PASSWORD", "")
    europe = bool(getattr(settings, "NAPOLEON_EUROPE", False))
    if not (email and password):
        raise FireplaceError("Napoleon credentials are not configured")

    client = NapoleonClient(email, password, europe=europe)
    try:
        await client.login()
        fireplaces = await client.fireplaces()
    except NapoleonError as exc:
        await _safe_close(client)
        raise FireplaceError(f"Napoleon login/discovery failed: {exc}") from exc

    _client = client
    _fireplaces = {fp.dsn: fp for fp in fireplaces}
    logger.info("Napoleon: discovered %d fireplace(s)", len(_fireplaces))


async def _safe_close(client: Any) -> None:
    try:
        await client.close()
    except Exception:  # pragma: no cover - best-effort cleanup
        pass


async def _reset() -> None:
    """Drop the cached client (forces a fresh login on the next call)."""
    global _client, _fireplaces
    client, _client = _client, None
    _fireplaces = {}
    if client is not None:
        await _safe_close(client)


def _state_to_dict(fp: Any) -> dict[str, Any]:
    """Serialize a Fireplace's cached state into a JSON-friendly dict."""
    s = fp.state

    def rgb(v: Any) -> list[int] | None:
        return list(v) if v is not None else None

    return {
        "dsn": fp.dsn,
        "name": fp.name,
        "online": fp.is_online,  # None = unknown
        "power": s.power,
        "flame_speed": s.flame_speed,
        "orange_flame": s.orange_flame,
        "yellow_flame": s.yellow_flame,
        "heater": s.heater,
        "setpoint_c": s.setpoint_c,
        "eco_mode": s.eco_mode,
        "boost_mode": s.boost_mode,
        "ember_bed_rgb": rgb(s.ember_bed_rgb),
        "ember_bed_brightness": s.ember_bed_brightness,
        "ember_bed_cycling": s.ember_bed_cycling,
        "top_light_rgb": rgb(s.top_light_rgb),
        "top_light_cycling": s.top_light_cycling,
        "current_favourite": s.current_favourite,
    }


# ---------------------------------------------------------------------------
# Coroutines (run on the loop thread)
# ---------------------------------------------------------------------------
async def _get_states() -> list[dict[str, Any]]:
    await _ensure_client()
    fps = list(_fireplaces.values())
    # Refresh all fireplaces concurrently.
    await asyncio.gather(*(fp.refresh() for fp in fps))
    return [_state_to_dict(fp) for fp in fps]


# action name -> coroutine factory taking (fireplace, value)
_ACTIONS: dict[str, Callable[[Any, Any], Coroutine[Any, Any, None]]] = {
    "power": lambda fp, v: fp.set_power(bool(v)),
    "flame_speed": lambda fp, v: fp.set_flame_speed(int(v)),
    "orange_flame": lambda fp, v: fp.set_orange_flame(int(v)),
    "yellow_flame": lambda fp, v: fp.set_yellow_flame(int(v)),
    "heater": lambda fp, v: fp.set_heater(int(v)),
    "setpoint_c": lambda fp, v: fp.set_setpoint_c(int(v)),
    "eco_mode": lambda fp, v: fp.set_eco_mode(bool(v)),
    "boost_mode": lambda fp, v: fp.set_boost_mode(bool(v)),
    "ember_bed_rgb": lambda fp, v: fp.set_ember_bed_rgb(tuple(int(c) for c in v)),
    "ember_bed_brightness": lambda fp, v: fp.set_ember_bed_brightness(int(v)),
    "ember_bed_cycling": lambda fp, v: fp.set_ember_bed_cycling(bool(v)),
    "top_light_rgb": lambda fp, v: fp.set_top_light_rgb(tuple(int(c) for c in v)),
    "top_light_cycling": lambda fp, v: fp.set_top_light_cycling(bool(v)),
    "favourite": lambda fp, v: fp.apply_favourite(str(v)),
}


async def _apply_action(dsn: str, action: str, value: Any) -> dict[str, Any]:
    from pynapoleon.errors import NapoleonError

    await _ensure_client()
    fp = _fireplaces.get(dsn)
    if fp is None:
        raise FireplaceError(f"Unknown fireplace: {dsn}")

    handler = _ACTIONS.get(action)
    if handler is None:
        raise FireplaceError(f"Unknown action: {action}")

    try:
        await handler(fp, value)
        # Reflect the change back to the caller.
        await fp.refresh()
    except NapoleonError as exc:
        raise FireplaceError(f"{action} failed: {exc}") from exc
    return _state_to_dict(fp)


# ---------------------------------------------------------------------------
# Public sync API (called from Django views) — with one auth/connection retry
# ---------------------------------------------------------------------------
def _run_with_retry(make_coro: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
    """Run a coroutine on the loop, retrying once after a fresh login.

    A cached client whose token/session has gone stale (process idle for a
    while, cloud-side session reaped, etc.) surfaces as a FireplaceError. We
    drop the cache, re-login, and retry exactly once before giving up.
    """
    loop = _loop()
    try:
        return loop.run(make_coro())
    except FireplaceError:
        logger.warning("Napoleon call failed; resetting client and retrying once")
        loop.run(_reset())
        return loop.run(make_coro())


def get_states() -> list[dict[str, Any]]:
    """Return the current state of every discovered fireplace."""
    return _run_with_retry(_get_states)


def apply_action(dsn: str, action: str, value: Any) -> dict[str, Any]:
    """Apply a single control action and return the refreshed fireplace state."""
    return _run_with_retry(lambda: _apply_action(dsn, action, value))
