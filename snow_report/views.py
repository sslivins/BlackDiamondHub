from django.shortcuts import render
from bs4 import BeautifulSoup
import requests
import re

def snow_report(request):
    # Fetch the HTML content from the URL
    url = 'https://www.sunpeaksresort.com/ski-ride/weather-conditions-cams/weather-snow-report'
    response = requests.get(url)
    html_content = response.content
    
    weather_data = parse_weather_html(html_content)
    
    print(weather_data)
    
    return render(request, 'snow_report.html', weather_data)

def parse_weather_html(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Extract today's weather
    today_weather = soup.find('div', class_='current-condition')
    sunpeaks_today_icon = today_weather.find('span', class_='icon')['class'][1]
    today_icon = map_weather_icon(sunpeaks_today_icon)
    today_description = today_weather.find('p', class_='today-description').text.strip()

    # Extract temperatures
    temperatures = []
    current_temps_section = soup.find('div', class_='half current-temps')
    for temp in current_temps_section.select('ul.list-temps li'):
        #print(temp.prettify())
        location = temp.find('h3').text.strip() if temp.find('h3') else ''
        elevation_text = temp.find('p').text.strip() if temp.find('p') else ''
        elevation = re.sub(r'[^\d]', '', elevation_text)  # Remove non-numeric characters
        elevation_unit = temp.find('span', class_='unit_switch').text.strip() if temp.find('span', class_='unit_switch') else ''
        value_span = temp.select_one('span.value_switch.value_deg')
        if not value_span:
            value_span = temp.select_one('span[class*="value_switch"][class*="value_deg"]')
        value = value_span.text.strip() if value_span else ''
        unit_span = temp.find('span', class_='unit_switch unit_deg')
        unit = unit_span.text.strip() if unit_span else ''
        temperatures.append({
            'location': location,
            'elevation': elevation,
            'elevation_unit': elevation_unit,
            'value': value,
            'unit': unit,
        })
        
    # Extract snow conditions
    snow_conditions = []
    for snow in soup.select('div#snow-conditions ul.list-snow:not(.snow-base) li'):
        period = snow.find('h4').text.strip() if snow.find('h4') else ''
        #if the period contains a trailing " *" remove it
        period = period.replace(' *', '')
        value_span = snow.find('span', class_='value_switch')
        value = value_span.text.strip() if value_span else 'N/A'
        unit_span = snow.find('span', class_='unit_switch')
        unit = unit_span.text.strip() if unit_span else ''
        snow_conditions.append({
            'period': period,
            'value': value,
            'unit': unit,
        })

    # Extract base snow conditions
    base_snow_conditions = []
    for base_snow in soup.select('ul.list-snow.snow-base li'):
        h4_element = base_snow.find('h4')
        if not h4_element or not h4_element.text.strip():
            continue  # Skip empty <li> elements
        period = h4_element.text.strip()
        value_span = base_snow.find('span', class_='value_switch')
        value = value_span.text.strip() if value_span else ''
        unit_span = base_snow.find('span', class_='unit_switch')
        unit = unit_span.text.strip() if unit_span else ''
        base_snow_conditions.append({
            'period': period,
            'value': value,
            'unit': unit,
        })

    # Extract wind speeds
    wind_speeds = []
    for wind in soup.find_all('div', class_='wind'):
        #print(wind.prettify())
        location = wind.find('h3').text.strip() if wind.find('h3') else ''
        elevation_text = wind.find('p').text.strip() if wind.find('p') else ''
        elevation = re.sub(r'[^\d]', '', elevation_text)  # Remove non-numeric characters
        elevation_unit = wind.find('span', class_='unit_switch').text.strip() if wind.find('span', class_='unit_switch') else ''
        speed_direction = wind.select_one('div.weather-value').text.strip() if wind.select_one('div.weather-value') else ''
        average_span = wind.select_one('span.value_switch.value_kph')
        speed_average = average_span.text.strip() if average_span else ''
        unit_span = wind.select_one('span.unit_switch.unit_kph')
        speed_unit = unit_span.text.strip() if unit_span else ''
        wind_speeds.append({
            'location': location,
            'elevation': elevation,
            'elevation_unit': elevation_unit,
            'speed_direction': speed_direction,
            'speed_average': speed_average,
            'speed_unit': speed_unit,
        })
        
    # Extract 5-day forecast
    forecast = []
    for day in soup.select('div#forecast div.third'):
        #print(day.prettify())
        day_name = day.find('h4').text.strip() if day.find('h4') else ''
        day_name = day_name.capitalize()
        
        icon_span = day.find('div', class_='day_conditions').find('span')
        sunpeaks_icon_class = next((cls for cls in icon_span.get('class', []) if cls.startswith('icon-')), None)
        icon_class = map_weather_icon(sunpeaks_icon_class) if sunpeaks_icon_class else "fas fa-question-circle"
        
        if icon_class == "fas fa-question-circle":
            print(f"Icon class not found for day: class: {sunpeaks_icon_class}")
        
        description_div = day.find('div', class_='day_description')
        description = description_div.get_text(strip=True) if description_div else None
        
        low_temp_span = day.find('span', class_='day_low')
        low_temp_value = low_temp_span.find('span', class_='value_switch').get_text(strip=True) if low_temp_span else None
        low_temp_unit = low_temp_span.find('span', class_='unit_switch').get_text(strip=True) if low_temp_span else None

        high_temp_span = day.find('span', class_='day_high')
        high_temp_value = high_temp_span.find('span', class_='value_switch').get_text(strip=True) if high_temp_span else None
        high_temp_unit = high_temp_span.find('span', class_='unit_switch').get_text(strip=True) if high_temp_span else None

        forecast.append({
            'day_name': day_name,
            'icon': icon_class,
            'description': description,
            'low_temp_value': low_temp_value,
            'low_temp_unit': low_temp_unit,
            'high_temp_value': high_temp_value,
            'high_temp_unit': high_temp_unit,
        })

    # Extract synopsis
    synopsis_div = soup.find('div', class_='field--name-field-synopsis')
    synopsis = synopsis_div.text.strip().replace('Synopsis:\xa0 ', '')

    # Extract extended outlook
    extended_outlook = soup.find('div', class_='field--name-field-extended-outlook').text.strip()

    return {
        'today_icon': today_icon,
        'today_description': today_description,
        'temperatures': temperatures,
        'snow_conditions': snow_conditions,
        'base_snow_conditions': base_snow_conditions,
        'wind_speeds': wind_speeds,
        'forecast': forecast,
        'synopsis': synopsis,
        'extended_outlook': extended_outlook,
    }
    
def map_weather_icon(sunpeaks_icon):
    """Maps Sun Peaks weather icon classes to FontAwesome or Weather Icons."""
    icon_mapping = {
        "icon-sunny_clear_skies": "fas fa-sun",  # Daytime clear sky
        "icon-clear_skies_night": "fas fa-moon",  # Nighttime clear sky
        "icon-partly_cloudy": "fas fa-cloud-sun",  # Partly cloudy
        "icon-mainly_cloudy": "fas fa-cloud",  # Mainly cloudy (more cloud cover than 'partly')
        "icon-cloudy": "fas fa-cloud",  # Cloudy
        "icon-overcast": "fas fa-smog",  # Overcast
        "icon-light_rain_showers": "fas fa-cloud-showers-light",  # Light rain
        "icon-rain_showers": "fas fa-cloud-rain",  # Rain showers
        "icon-snow_showers": "fas fa-snowflake",  # Snow showers
        "icon-light_snow": "fas fa-snowflake",  # Light snow
        "icon-snow": "fas fa-snowman",  # Snow
        "icon-heavy_snow": "fas fa-snowman",  # Heavy snow
        "icon-thunderstorm": "fas fa-bolt",  # Thunderstorm
        "icon-fog": "fas fa-smog",  # Fog
    }
    return icon_mapping.get(sunpeaks_icon, "fas fa-question-circle")  # Default to '?' if not found

