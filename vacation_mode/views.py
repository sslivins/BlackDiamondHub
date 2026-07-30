from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET
import json

from .executor import (
    get_away_mode_state,
    get_current_season,
    start_execution,
    get_run_status,
    get_active_run,
)
from .steps import build_vacation_steps, build_home_steps, SEASON_COOLING


def vacation_mode_view(request):
    """Main page view — renders the vacation mode UI."""
    is_away = get_away_mode_state()
    active_run = get_active_run()

    # Determine which steps to show based on current state
    if active_run:
        # If a run is in progress, show those steps
        mode = active_run["mode"]
        steps = active_run["steps"]
        run_id = active_run["run_id"]
        season = active_run.get("season")
        season_avg = active_run.get("season_avg")
    else:
        # Show the steps for the action they'd take next, for the season the
        # system would pick right now.
        season, season_avg = get_current_season()
        mode = "home" if is_away else "vacation"
        steps_def = (
            build_home_steps(season) if is_away else build_vacation_steps(season)
        )
        steps = [
            {"alias": s["alias"], "icon": s["icon"], "status": "pending", "attempt": 0, "error": None, "progress": None}
            for s in steps_def
        ]
        run_id = None

    context = {
        "is_away": is_away,
        "mode": mode,
        "steps": json.dumps(steps),
        "run_id": run_id,
        "active_run": active_run is not None,
        "season": season,
        "season_is_cooling": season == SEASON_COOLING,
        "season_avg": season_avg,
    }
    return render(request, "vacation_mode.html", context)


@require_POST
def execute_view(request):
    """API endpoint to start executing vacation or home mode steps."""
    try:
        body = json.loads(request.body)
        mode = body.get("mode")
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    if mode not in ("vacation", "home"):
        return JsonResponse({"error": "Invalid mode. Must be 'vacation' or 'home'"}, status=400)

    dry_run = body.get("dry_run", False)
    skip_steps = body.get("skip_steps", [])

    run_id, error = start_execution(mode, dry_run=dry_run, skip_steps=skip_steps)
    if error:
        return JsonResponse({"error": error}, status=409)

    return JsonResponse({"run_id": run_id, "mode": mode})


@require_GET
def status_view(request, run_id):
    """API endpoint to poll the status of a run."""
    run_data = get_run_status(run_id)
    if not run_data:
        return JsonResponse({"error": "Run not found"}, status=404)

    return JsonResponse(run_data)


@require_GET
def state_view(request):
    """API endpoint to get current away mode state and any active run."""
    is_away = get_away_mode_state()
    active_run = get_active_run()

    return JsonResponse({
        "is_away": is_away,
        "active_run": {
            "run_id": active_run["run_id"],
            "mode": active_run["mode"],
            "steps": active_run["steps"],
        } if active_run else None,
    })
