import os
import requests
from django.test import TestCase
from snow_report.views import parse_weather_html

class LiveParseWeatherHtmlTests(TestCase):
    def parse_weather_html_live_data_and_test(self, units=""):
        url = "https://www.sunpeaksresort.com/ski-ride/weather-conditions-cams/weather-snow-report"
        response = requests.get(url)
        html_content = response.content

        weather_data_metric = parse_weather_html(html_content, units)
        self.assertIsNotNone(weather_data_metric)

        # Ensure today_icon is mapped correctly
        today_icon = weather_data_metric["today_icon"]
        self.assertNotEqual(today_icon, "fas fa-question-circle", f"today_icon is set to unknown value {today_icon}")

        # Ensure today_description is not empty
        today_description = weather_data_metric["today_description"]
        self.assertNotEqual(today_description, "", "today_description is empty")

        ##########################
        ## Temperatures
        ##########################
        temperatures = weather_data_metric["temperatures"]
        self.assertEqual(len(temperatures), 4, f"Expected 4 temperature readings but found {len(temperatures)}")

        for temp in temperatures:
            self.assertNotEqual(temp["location"], "", f"Temperature location for {temp['location']} is empty")
            self.assertNotEqual(temp["elevation"], "", f"Temperature elevation for {temp['location']} is empty")

            try:
                temp_value = int(temp["elevation"])
                self.assertGreaterEqual(temp_value, 1000, f"Elevation of {temp['elevation']} for {temp['location']} is less than 1000")
                self.assertLessEqual(temp_value, 10000, f"Elevation of {temp['elevation']} for {temp['location']} is greater than 10000")
            except ValueError:
                self.fail(f"Elevation value for {temp['location']} is not a valid integer: {temp['elevation']}")

        expected_unit = "ft" if units == "imperial" else "m"
        for temp in temperatures:
            self.assertEqual(temp["elevation_unit"], expected_unit, f"Elevation unit for {temp['location']} is {temp['elevation_unit']} - expected: {expected_unit}")

        for temp in temperatures:
            self.assertNotEqual(temp["value"], "", f"Temperature value for {temp['location']} is empty")

            try:
                temp_value = int(temp["value"])
                self.assertGreaterEqual(temp_value, -50, f"Temperature of {temp['value']} for {temp['location']} is less than -50")
                self.assertLessEqual(temp_value, 120, f"Temperature of {temp['value']} for {temp['location']} is greater than 120")
            except ValueError:
                self.fail(f"Temperature value for {temp['location']} is not a valid integer: {temp['value']}")

        expected_unit = "°F" if units == "imperial" else "°C"
        for temp in temperatures:
            self.assertEqual(temp["unit"], expected_unit, f"Temperature unit for {temp['location']} is {temp['unit']} - expected: {expected_unit}")

        ##########################
        ## Snow Conditions
        ##########################
        snow_conditions = weather_data_metric["snow_conditions"]
        self.assertEqual(len(snow_conditions), 4, f"Expected 4 snow conditions but found: {len(snow_conditions)}")

        for snow in snow_conditions:
            self.assertNotEqual(snow["period"], "", f"Snow condition period for {snow['period']} is empty")
            self.assertNotEqual(snow["value"], "", f"Snow condition value for {snow['period']} is empty")

        expected_unit = "in" if units == "imperial" else "cm"
        for snow in snow_conditions:
            self.assertEqual(snow["unit"], expected_unit, f"Snow condition unit for {snow['period']} is {snow['unit']} - expected: {expected_unit}")

        ##########################
        ## Wind Speeds
        ##########################
        wind_speeds = weather_data_metric["wind_speeds"]
        self.assertEqual(len(wind_speeds), 4, f"Expected 4 wind speeds but found {len(wind_speeds)}")

        for wind in wind_speeds:
            self.assertNotEqual(wind["location"], "", f"Wind speed location for {wind['location']} is empty")
            self.assertNotEqual(wind["elevation"], "", f"Wind speed elevation for {wind['location']} is empty")

            try:
                temp_value = int(wind["elevation"])
                self.assertGreaterEqual(temp_value, 1000, f"Elevation of {wind['elevation']} for {wind['location']} is less than 1000")
                self.assertLessEqual(temp_value, 10000, f"Elevation of {wind['elevation']} for {wind['location']} is greater than 10000")
            except ValueError:
                self.fail(f"Elevation value for {wind['location']} is not a valid integer: {wind['elevation']}")

        for wind in wind_speeds:
            self.assertNotEqual(wind["speed_direction"], "", f"Wind speed direction for {wind['location']} is empty")
            self.assertNotEqual(wind["speed_average"], "", f"Wind speed average for {wind['location']} is empty")

            try:
                temp_value = int(wind["speed_average"])
                self.assertGreaterEqual(temp_value, 0, f"Wind speed of {wind['speed_average']} for {wind['location']} is less than 0")
                self.assertLessEqual(temp_value, 150, f"Wind speed of {wind['speed_average']} for {wind['location']} is greater than 150")
            except ValueError:
                self.fail(f"Wind speed value for {wind['location']} is not a valid integer: {wind['speed_average']}")

        expected_unit = "mph" if units == "imperial" else "kph"
        for wind in wind_speeds:
            self.assertEqual(wind["speed_unit"], expected_unit, f"Wind speed unit for {wind['location']} is {wind['speed_unit']} - expected: {expected_unit}")

        ##########################
        ## Forecast
        ##########################
        forecast = weather_data_metric["forecast"]
        self.assertEqual(len(forecast), 6, f"Expected 6 forecast items but found {len(forecast)}")

        for day in forecast:
            self.assertNotEqual(day["day_name"], "", f"Forecast day name for {day['day_name']} is empty")
            self.assertTrue(day["day_name"].startswith(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")), f"Forecast day name for {day['day_name']} is not a valid day of the week")
            self.assertNotEqual(day["icon"], "", f"Forecast icon for {day['day_name']} is empty")
            self.assertNotEqual(day["icon"], "fas fa-question-circle", f"Forecast icon for {day['day_name']} is set to an unknown icon (check mapping)")
            self.assertNotEqual(day["description"], "", f"Forecast description for {day['day_name']} is empty")

        expected_unit = "°F" if units == "imperial" else "°C"
        for day in forecast:
            self.assertEqual(day["temp_unit"], expected_unit, f"Forecast temp unit for {day['day_name']} is {day['temp_unit']} - expected: {expected_unit}")

    def test_parse_weather_html_live_data_imperial(self):
        self.parse_weather_html_live_data_and_test("imperial")

    def test_parse_weather_html_live_data_metric(self):
        self.parse_weather_html_live_data_and_test("metric")

    def test_parse_weather_html_live_data_empty(self):
        self.parse_weather_html_live_data_and_test("")

    def test_parse_weather_html_live_data_invalid_unit(self):
        self.parse_weather_html_live_data_and_test("invalid_unit")

                    
class OfflineParseWeatherHtmlTests(TestCase):
    def test_parse_weather_html_bad_data(self):
        # Load the sample bad data HTML file
        file_path = os.path.join(os.path.dirname(__file__), 'tests', 'weather_bad_data.html')
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        weather_data_metric = parse_weather_html(html_content, "metric")        
        #the 24hr value for snow_conditions should be empty
        #loop through the snow_conditions list and find where period == "24 hr"
        found = False
        for snow in weather_data_metric["snow_conditions"]:
          print(snow)
          if snow["period"] == "24 Hr":
              self.assertEqual(snow["value"], "N/A", f"24 hr snow condition should be empty but found: {snow['value']}")
              found = True
              break
              
        self.assertTrue(found, "Did not find 24 hr snow condition in the list")
        
        
        
        # # Test with metric units

        # self.assertIsNotNone(weather_data_metric)
        # self.assertNotIn('', weather_data_metric.values(), "Empty string found in metric weather data")
        # self.assertNotIn('', [item for sublist in weather_data_metric.values() if isinstance(sublist, list) for item in sublist], "Empty string found in metric weather data list items")

        # # Test with imperial units
        # weather_data_imperial = parse_weather_html(html_content, "imperial")
        # self.assertIsNotNone(weather_data_imperial)
        # self.assertNotIn('', weather_data_imperial.values(), "Empty string found in imperial weather data")
        # self.assertNotIn('', [item for sublist in weather_data_imperial.values() if isinstance(sublist, list) for item in sublist], "Empty string found in imperial weather data list items")