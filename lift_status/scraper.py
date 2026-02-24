import requests
from bs4 import BeautifulSoup
from html import unescape


# The Sun Peaks lift/trail status page URL
LIFT_STATUS_URL = (
    "https://www.sunpeaksresort.com/ski-ride/"
    "weather-conditions-cams/lifts-trail-status"
)

# Zone keys → display names (order determines tab order)
ZONES = [
    ("mt-morrisey", "Mt. Morrisey"),
    ("sundance", "Sundance"),
    ("tod-mountain", "Tod Mountain"),
    ("orient-ridge", "Orient Ridge"),
]

# Difficulty slug → display name (ordered easiest → hardest)
DIFFICULTY_ORDER = [
    "1-easiest",
    "2-more-difficult",
    "3-most-difficult",
    "4-experts-only",
    "5-park",
    "5-black-diamond-park",
    "6-glades",
]

DIFFICULTY_LABELS = {
    "1-easiest": "Easiest",
    "2-more-difficult": "More Difficult",
    "2-intermediate": "Intermediate",
    "3-most-difficult": "Most Difficult",
    "3-advanced": "Advanced",
    "4-experts-only": "Experts Only",
    "4-expert": "Expert",
    "5-park": "Terrain Park",
    "5-black-diamond-park": "Terrain Park",
    "6-glades": "Glades",
}

# CSS class → Font Awesome icon class for difficulty indicators
DIFFICULTY_ICONS = {
    "1-easiest": "fa-circle text-success",
    "2-more-difficult": "fa-square text-primary",
    "2-intermediate": "fa-square text-primary",
    "3-most-difficult": "fa-diamond text-dark",
    "3-advanced": "fa-diamond text-dark",
    "4-experts-only": "fa-diamond text-dark",
    "4-expert": "fa-diamond text-dark",
    "5-park": "fa-square-full text-warning",
    "5-black-diamond-park": "fa-square-full text-warning",
    "6-glades": "fa-tree text-success",
}


def fetch_lift_status_html():
    """Fetch the raw HTML from the Sun Peaks lift/trail status page."""
    response = requests.get(LIFT_STATUS_URL, timeout=15)
    response.raise_for_status()
    return response.content


def parse_lift_status(html):
    """Parse the lift/trail status HTML and return structured data.

    Returns a dict with:
        - lifts: list of lift dicts
        - zones: list of (zone_key, zone_label, trails_by_difficulty) tuples
    """
    soup = BeautifulSoup(html, "html.parser")

    lifts = _parse_lifts(soup)
    zones = _parse_trails_by_zone(soup)

    return {"lifts": lifts, "zones": zones}


def _parse_lifts(soup):
    """Extract all lift status entries."""
    lifts = []
    for article in soup.find_all("article", class_="node-type-lift"):
        name_span = article.find("span", class_="field--name-title")
        name = unescape(name_span.get_text(strip=True)) if name_span else ""

        notes_span = article.find("span", class_="notes")
        notes = unescape(notes_span.get_text(strip=True)) if notes_span else ""

        # Status: icon-open or icon-close span
        status_cell = article.find("div", class_="row-cell status")
        status = "unknown"
        if status_cell:
            if status_cell.find("span", class_="icon-open"):
                status = "open"
            elif status_cell.find("span", class_="icon-close"):
                status = "closed"

        lifts.append({
            "name": name,
            "status": status,
            "notes": notes,
        })

    return lifts


def _parse_trails_by_zone(soup):
    """Extract trail data grouped by zone, then by difficulty."""
    # Collect all trails first
    trails_by_zone = {key: [] for key, _ in ZONES}

    for article in soup.find_all("article", class_="node-type-trail"):
        classes = article.get("class", [])

        name_span = article.find("span", class_="field--name-title")
        name = unescape(name_span.get_text(strip=True)) if name_span else ""

        # Determine zone from cat- classes
        zone = None
        for zone_key, _ in ZONES:
            if f"cat-{zone_key}" in classes:
                zone = zone_key
                break

        if zone is None:
            continue  # skip trails without a known zone

        # Determine difficulty from cat- classes
        difficulty = "unknown"
        for diff_key in DIFFICULTY_ORDER:
            if f"cat-{diff_key}" in classes:
                difficulty = diff_key
                break

        # Grooming status from icon-tick span
        grooming = "none"
        status_cell = article.find("div", class_="row-cell status")
        if status_cell:
            tick = status_cell.find("span", class_=lambda c: c and "icon-tick" in c)
            if tick:
                tick_classes = tick.get("class", [])
                if "groomed-with-fresh" in tick_classes:
                    grooming = "groomed-with-fresh"
                elif "groomed" in tick_classes:
                    grooming = "groomed"

        trails_by_zone[zone].append({
            "name": name,
            "difficulty": difficulty,
            "difficulty_label": DIFFICULTY_LABELS.get(difficulty, difficulty),
            "difficulty_icon": DIFFICULTY_ICONS.get(difficulty, ""),
            "grooming": grooming,
        })

    # Build ordered zone list with trails grouped by difficulty
    zones = []
    for zone_key, zone_label in ZONES:
        trails = trails_by_zone[zone_key]
        # Group by difficulty in order
        trails_by_diff = []
        seen_diffs = set()
        for diff_key in DIFFICULTY_ORDER:
            diff_trails = [t for t in trails if t["difficulty"] == diff_key]
            if diff_trails and diff_key not in seen_diffs:
                seen_diffs.add(diff_key)
                trails_by_diff.append({
                    "difficulty_key": diff_key,
                    "difficulty_label": DIFFICULTY_LABELS.get(diff_key, diff_key),
                    "difficulty_icon": DIFFICULTY_ICONS.get(diff_key, ""),
                    "trails": sorted(diff_trails, key=lambda t: t["name"]),
                })

        zones.append({
            "key": zone_key,
            "label": zone_label,
            "trail_count": len(trails),
            "trails_by_difficulty": trails_by_diff,
        })

    return zones


def get_lift_status():
    """Fetch and parse lift/trail status, with 5-minute cache.

    The scrape takes a few seconds, so we cache the result to make
    subsequent page loads instant.  The default Django LocMemCache is
    fine because we run a single Daphne process.
    """
    from django.core.cache import cache

    CACHE_KEY = "lift_status_data"
    CACHE_TTL = 5 * 60  # 5 minutes

    data = cache.get(CACHE_KEY)
    if data is None:
        html = fetch_lift_status_html()
        data = parse_lift_status(html)
        cache.set(CACHE_KEY, data, CACHE_TTL)
    return data
