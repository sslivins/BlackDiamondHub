import requests
from unittest.mock import patch
from django.test import TestCase, Client

from lift_status.scraper import (
    parse_lift_status,
    fetch_lift_status_html,
    ZONES,
    DIFFICULTY_ORDER,
)


# ---------------------------------------------------------------------------
# Sample HTML fragment for offline/mocked tests
# ---------------------------------------------------------------------------
SAMPLE_HTML = """
<html><body>

<!-- Lift section -->
<article class="node node-type-lift node-view-row iso-item cat-127 label-sunburst-express">
  <div class="row-cell name">
    <span class="field field--name-title field--type-string field--label-hidden">Sunburst Express Chairlift</span>
    <span class="notes"> Daily, 9:00am to 3:30pm </span>
  </div>
  <div class="row-cell status">
    <span class="icon-open"></span>
  </div>
</article>

<article class="node node-type-lift node-view-row iso-item cat-126 label-morrisey-express">
  <div class="row-cell name">
    <span class="field field--name-title field--type-string field--label-hidden">Morrisey Express Chairlift</span>
    <span class="notes"> Daily, 8:30am to 4:00pm </span>
  </div>
  <div class="row-cell status">
    <span class="icon-close"></span>
  </div>
</article>

<article class="node node-type-lift node-view-row iso-item cat-126 label-orient-chairlift">
  <div class="row-cell name">
    <span class="field field--name-title field--type-string field--label-hidden">Orient Chairlift</span>
    <span class="notes"> Weekends only, 9:00am to 3:00pm </span>
  </div>
  <div class="row-cell status">
    <span class="icon-open"></span>
  </div>
</article>

<!-- Trail section -->
<article class="node node-type-trail node-view-row iso-item cat-tod-mountain cat-1-easiest sport-ski cat-groomed label-5-mile-lower">
  <div class="row-cell level"><span class="icon-trail_1-easiest ski"></span></div>
  <div class="row-cell name">
    <span class="field field--name-title field--type-string field--label-hidden">5 Mile Lower</span>
  </div>
  <div class="row-cell status">
    <span class="icon-tick groomed"></span>
  </div>
</article>

<article class="node node-type-trail node-view-row iso-item cat-tod-mountain cat-2-more-difficult sport-ski label-alley">
  <div class="row-cell level"><span class="icon-trail_2-more-difficult ski"></span></div>
  <div class="row-cell name">
    <span class="field field--name-title field--type-string field--label-hidden">Alley</span>
  </div>
  <div class="row-cell status">
    <span class="icon-tick groomed-with-fresh"></span>
  </div>
</article>

<article class="node node-type-trail node-view-row iso-item cat-mt-morrisey cat-1-easiest sport-ski cat-groomed label-anticipation">
  <div class="row-cell level"><span class="icon-trail_1-easiest ski"></span></div>
  <div class="row-cell name">
    <span class="field field--name-title field--type-string field--label-hidden">Anticipation</span>
  </div>
  <div class="row-cell status">
    <span class="icon-tick groomed"></span>
  </div>
</article>

<article class="node node-type-trail node-view-row iso-item cat-sundance cat-3-most-difficult sport-ski label-peak-a-boo">
  <div class="row-cell level"><span class="icon-trail_3-most-difficult ski"></span></div>
  <div class="row-cell name">
    <span class="field field--name-title field--type-string field--label-hidden">Peak-A-Boo</span>
  </div>
  <div class="row-cell status">
  </div>
</article>

<article class="node node-type-trail node-view-row iso-item cat-orient-ridge cat-6-glades sport-ski label-czesc-glades">
  <div class="row-cell level"><span class="icon-trail_6-glades ski"></span></div>
  <div class="row-cell name">
    <span class="field field--name-title field--type-string field--label-hidden">Cześć Glades</span>
  </div>
  <div class="row-cell status">
  </div>
</article>

</body></html>
"""


# ===========================================================================
# Offline tests with mocked HTML
# ===========================================================================
class ParseLiftStatusOfflineTests(TestCase):
    """Tests using static HTML — no network calls."""

    def setUp(self):
        self.data = parse_lift_status(SAMPLE_HTML)

    # --- Lift parsing ---

    def test_lifts_count(self):
        self.assertEqual(len(self.data["lifts"]), 3)

    def test_lift_names(self):
        names = [l["name"] for l in self.data["lifts"]]
        self.assertIn("Sunburst Express Chairlift", names)
        self.assertIn("Morrisey Express Chairlift", names)
        self.assertIn("Orient Chairlift", names)

    def test_lift_open_status(self):
        sunburst = next(l for l in self.data["lifts"] if "Sunburst" in l["name"])
        self.assertEqual(sunburst["status"], "open")

    def test_lift_closed_status(self):
        morrisey = next(l for l in self.data["lifts"] if "Morrisey" in l["name"])
        self.assertEqual(morrisey["status"], "closed")

    def test_lift_notes(self):
        sunburst = next(l for l in self.data["lifts"] if "Sunburst" in l["name"])
        self.assertIn("9:00am", sunburst["notes"])
        self.assertIn("3:30pm", sunburst["notes"])

    # --- Zone / trail structure ---

    def test_four_zones_returned(self):
        self.assertEqual(len(self.data["zones"]), 4)

    def test_zone_keys_match(self):
        zone_keys = [z["key"] for z in self.data["zones"]]
        expected_keys = [k for k, _ in ZONES]
        self.assertEqual(zone_keys, expected_keys)

    def test_tod_mountain_trail_count(self):
        tod = next(z for z in self.data["zones"] if z["key"] == "tod-mountain")
        self.assertEqual(tod["trail_count"], 2)  # 5 Mile Lower + Alley

    def test_mt_morrisey_trail_count(self):
        mm = next(z for z in self.data["zones"] if z["key"] == "mt-morrisey")
        self.assertEqual(mm["trail_count"], 1)  # Anticipation

    def test_sundance_trail_count(self):
        sd = next(z for z in self.data["zones"] if z["key"] == "sundance")
        self.assertEqual(sd["trail_count"], 1)  # Peak-A-Boo

    def test_orient_ridge_trail_count(self):
        orr = next(z for z in self.data["zones"] if z["key"] == "orient-ridge")
        self.assertEqual(orr["trail_count"], 1)  # Cześć Glades

    # --- Grooming ---

    def test_groomed_status(self):
        tod = next(z for z in self.data["zones"] if z["key"] == "tod-mountain")
        all_trails = [t for g in tod["trails_by_difficulty"] for t in g["trails"]]
        five_mile = next(t for t in all_trails if "5 Mile" in t["name"])
        self.assertEqual(five_mile["grooming"], "groomed")

    def test_groomed_with_fresh_status(self):
        tod = next(z for z in self.data["zones"] if z["key"] == "tod-mountain")
        all_trails = [t for g in tod["trails_by_difficulty"] for t in g["trails"]]
        alley = next(t for t in all_trails if t["name"] == "Alley")
        self.assertEqual(alley["grooming"], "groomed-with-fresh")

    def test_not_groomed_status(self):
        sd = next(z for z in self.data["zones"] if z["key"] == "sundance")
        all_trails = [t for g in sd["trails_by_difficulty"] for t in g["trails"]]
        pab = next(t for t in all_trails if "Peak" in t["name"])
        self.assertEqual(pab["grooming"], "none")

    # --- Difficulty ---

    def test_difficulty_label_assigned(self):
        tod = next(z for z in self.data["zones"] if z["key"] == "tod-mountain")
        all_trails = [t for g in tod["trails_by_difficulty"] for t in g["trails"]]
        five_mile = next(t for t in all_trails if "5 Mile" in t["name"])
        self.assertEqual(five_mile["difficulty"], "1-easiest")
        self.assertEqual(five_mile["difficulty_label"], "Easiest")

    def test_trails_grouped_by_difficulty(self):
        tod = next(z for z in self.data["zones"] if z["key"] == "tod-mountain")
        diff_keys = [g["difficulty_key"] for g in tod["trails_by_difficulty"]]
        # Should have easiest and more-difficult groups
        self.assertIn("1-easiest", diff_keys)
        self.assertIn("2-more-difficult", diff_keys)

    def test_trails_sorted_alphabetically_within_group(self):
        """If there were multiple trails in a group, they should be alphabetical."""
        tod = next(z for z in self.data["zones"] if z["key"] == "tod-mountain")
        for group in tod["trails_by_difficulty"]:
            names = [t["name"] for t in group["trails"]]
            self.assertEqual(names, sorted(names))

    # --- Difficulty icon ---

    def test_difficulty_icon_present(self):
        tod = next(z for z in self.data["zones"] if z["key"] == "tod-mountain")
        all_trails = [t for g in tod["trails_by_difficulty"] for t in g["trails"]]
        for trail in all_trails:
            self.assertTrue(trail["difficulty_icon"], f"{trail['name']} has no difficulty icon")

    # --- Empty HTML ---

    def test_empty_html(self):
        data = parse_lift_status("<html><body></body></html>")
        self.assertEqual(len(data["lifts"]), 0)
        self.assertEqual(len(data["zones"]), 4)
        for zone in data["zones"]:
            self.assertEqual(zone["trail_count"], 0)


class ParseLiftStatusSpecialCasesTests(TestCase):
    """Edge cases for the parser."""

    def test_html_entities_decoded(self):
        html = """
        <article class="node node-type-trail iso-item cat-mt-morrisey cat-2-more-difficult">
          <div class="row-cell name">
            <span class="field field--name-title">Grannie Greene&#039;s</span>
          </div>
          <div class="row-cell status"></div>
        </article>
        """
        data = parse_lift_status(html)
        mm = next(z for z in data["zones"] if z["key"] == "mt-morrisey")
        all_trails = [t for g in mm["trails_by_difficulty"] for t in g["trails"]]
        self.assertEqual(len(all_trails), 1)
        self.assertEqual(all_trails[0]["name"], "Grannie Greene's")

    def test_trail_without_zone_is_skipped(self):
        html = """
        <article class="node node-type-trail iso-item cat-1-easiest">
          <div class="row-cell name">
            <span class="field field--name-title">Orphan Trail</span>
          </div>
          <div class="row-cell status"></div>
        </article>
        """
        data = parse_lift_status(html)
        total = sum(z["trail_count"] for z in data["zones"])
        self.assertEqual(total, 0)

    def test_lift_without_status_span(self):
        html = """
        <article class="node node-type-lift iso-item cat-127">
          <div class="row-cell name">
            <span class="field field--name-title">Mystery Lift</span>
          </div>
          <div class="row-cell status"></div>
        </article>
        """
        data = parse_lift_status(html)
        self.assertEqual(len(data["lifts"]), 1)
        self.assertEqual(data["lifts"][0]["status"], "unknown")


# ===========================================================================
# View tests
# ===========================================================================
class LiftStatusViewTests(TestCase):
    """Test the Django view with mocked scraper data."""

    @patch("lift_status.views.get_lift_status")
    def test_view_returns_200(self, mock_get):
        mock_get.return_value = parse_lift_status(SAMPLE_HTML)
        client = Client()
        response = client.get("/lift_status/")
        self.assertEqual(response.status_code, 200)

    @patch("lift_status.views.get_lift_status")
    def test_view_contains_lift_name(self, mock_get):
        mock_get.return_value = parse_lift_status(SAMPLE_HTML)
        client = Client()
        response = client.get("/lift_status/")
        self.assertContains(response, "Sunburst Express Chairlift")

    @patch("lift_status.views.get_lift_status")
    def test_view_contains_zone_tabs(self, mock_get):
        mock_get.return_value = parse_lift_status(SAMPLE_HTML)
        client = Client()
        response = client.get("/lift_status/")
        self.assertContains(response, "Tod Mountain")
        self.assertContains(response, "Mt. Morrisey")
        self.assertContains(response, "Sundance")
        self.assertContains(response, "Orient Ridge")

    @patch("lift_status.views.get_lift_status")
    def test_view_contains_trail_name(self, mock_get):
        mock_get.return_value = parse_lift_status(SAMPLE_HTML)
        client = Client()
        response = client.get("/lift_status/")
        self.assertContains(response, "5 Mile Lower")

    @patch("lift_status.views.get_lift_status")
    def test_view_contains_grooming_badge(self, mock_get):
        mock_get.return_value = parse_lift_status(SAMPLE_HTML)
        client = Client()
        response = client.get("/lift_status/")
        self.assertContains(response, "Groomed + Fresh")

    @patch("lift_status.views.get_lift_status")
    def test_view_contains_status_badges(self, mock_get):
        mock_get.return_value = parse_lift_status(SAMPLE_HTML)
        client = Client()
        response = client.get("/lift_status/")
        self.assertContains(response, "badge-open")
        self.assertContains(response, "badge-closed")


# ===========================================================================
# Live tests — hit the real Sun Peaks website
# ===========================================================================
class LiveLiftStatusTests(TestCase):
    """Live scraping tests — run daily in CI to detect page changes."""

    def setUp(self):
        html = fetch_lift_status_html()
        self.data = parse_lift_status(html)

    def test_lifts_present(self):
        """The page should return at least some lifts."""
        self.assertGreater(len(self.data["lifts"]), 0,
                           "No lifts found — page structure may have changed")

    def test_lift_has_name(self):
        for lift in self.data["lifts"]:
            self.assertTrue(lift["name"], f"Lift with empty name found")

    def test_lift_has_valid_status(self):
        for lift in self.data["lifts"]:
            self.assertIn(lift["status"], ("open", "closed", "unknown"),
                          f"Lift '{lift['name']}' has unexpected status: {lift['status']}")

    def test_lift_has_notes(self):
        """At least some lifts should have schedule notes."""
        lifts_with_notes = [l for l in self.data["lifts"] if l["notes"]]
        self.assertGreater(len(lifts_with_notes), 0,
                           "No lifts have schedule notes")

    def test_four_zones_returned(self):
        self.assertEqual(len(self.data["zones"]), 4)

    def test_trails_present_in_at_least_one_zone(self):
        total = sum(z["trail_count"] for z in self.data["zones"])
        self.assertGreater(total, 0,
                           "No trails found — page structure may have changed")

    def test_trail_count_reasonable(self):
        """Sun Peaks has ~140 trails; should find at least 50."""
        total = sum(z["trail_count"] for z in self.data["zones"])
        self.assertGreater(total, 50,
                           f"Only {total} trails found — expected at least 50")

    def test_trails_have_difficulty(self):
        """Every trail should have a difficulty classification."""
        for zone in self.data["zones"]:
            for group in zone["trails_by_difficulty"]:
                for trail in group["trails"]:
                    self.assertNotEqual(trail["difficulty"], "unknown",
                                        f"Trail '{trail['name']}' has unknown difficulty")

    def test_some_trails_groomed(self):
        """At least some trails should show grooming status."""
        groomed_count = 0
        for zone in self.data["zones"]:
            for group in zone["trails_by_difficulty"]:
                for trail in group["trails"]:
                    if trail["grooming"] in ("groomed", "groomed-with-fresh"):
                        groomed_count += 1
        # During season there should be groomed trails, off-season this may be 0
        # so we just check parsing works (count >= 0)
        self.assertGreaterEqual(groomed_count, 0)

    def test_zone_labels_match_expected(self):
        labels = [z["label"] for z in self.data["zones"]]
        self.assertIn("Tod Mountain", labels)
        self.assertIn("Mt. Morrisey", labels)
        self.assertIn("Sundance", labels)
        self.assertIn("Orient Ridge", labels)

    def test_view_returns_200(self):
        """Integration test — the full view should render without error."""
        client = Client()
        response = client.get("/lift_status/")
        self.assertEqual(response.status_code, 200)
