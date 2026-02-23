from django.shortcuts import render
from .scraper import get_lift_status


def lift_status_view(request):
    """Display lift and trail status with zone-based tabs."""
    data = get_lift_status()
    return render(request, "lift_status.html", data)
