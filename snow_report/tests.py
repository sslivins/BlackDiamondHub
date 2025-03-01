import requests
from django.test import TestCase
from snow_report.views import parse_weather_html

class LiveParseWeatherHtmlTests(TestCase):
    def test_parse_weather_html_live_data(self):
        url = "https://www.sunpeaksresort.com/ski-ride/weather-conditions-cams/weather-snow-report"
        response = requests.get(url)
        html_content = response.content

        # Test with metric units
        weather_data_metric = parse_weather_html(html_content, "metric")
        self.assertIsNotNone(weather_data_metric)
        self.assertNotIn('', weather_data_metric.values(), "Empty string found in metric weather data")
        self.assertNotIn('', [item for sublist in weather_data_metric.values() if isinstance(sublist, list) for item in sublist], "Empty string found in metric weather data list items")

        # Test with imperial units
        weather_data_imperial = parse_weather_html(html_content, "imperial")
        self.assertIsNotNone(weather_data_imperial)
        self.assertNotIn('', weather_data_imperial.values(), "Empty string found in imperial weather data")
        self.assertNotIn('', [item for sublist in weather_data_imperial.values() if isinstance(sublist, list) for item in sublist], "Empty string found in imperial weather data list items")