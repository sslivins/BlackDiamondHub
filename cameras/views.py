import json
import logging
import urllib.request
import urllib.error

from django.shortcuts import render
from django.conf import settings

logger = logging.getLogger(__name__)


def get_go2rtc_streams(go2rtc_url):
    """Fetch the list of configured streams from go2rtc API."""
    try:
        req = urllib.request.Request(f'{go2rtc_url}/api/streams')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            return [
                {
                    'name': name,
                    'display_name': name.replace('_', ' ').replace('-', ' ').title(),
                }
                for name in sorted(data.keys())
            ]
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to fetch streams from go2rtc at %s: %s", go2rtc_url, e)
        return []


def camera_feed_view(request):
    """View to display camera feeds via go2rtc."""
    go2rtc_url = getattr(settings, 'GO2RTC_URL', 'http://localhost:1984')
    streams = get_go2rtc_streams(go2rtc_url)

    return render(request, 'camera_feeds.html', {
        'streams': streams,
        'go2rtc_url': go2rtc_url,
    })
