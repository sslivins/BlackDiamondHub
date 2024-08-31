from django.shortcuts import render
import requests
from requests.exceptions import RequestException
from django.http import HttpResponse
from bs4 import BeautifulSoup
import re

def landing_page(request):
    url = 'https://www.sunpeaksresort.com/bike-hike/weather-webcams/weather'  # Replace with the URL you want to fetch
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract the current weather
        current_weather = soup.find('div', {'class': 'weather current-conditions'})  # Adjust as needed        
    except RequestException as e:
        print(f"Failed to fetch content from {url}")
        content = "Error Loading Weather"
        
    soup = BeautifulSoup(str(current_weather), 'html.parser')
    
    weather_data = []

    # Find all list items under the class "list-temps"
    list_temps = soup.select('ul.list-temps li')

    # Iterate over each item and extract the relevant data
    for item in list_temps:
        location = item.find('h3').text
        
        # Extract the elevation, remove non-numeric characters, and convert to an integer
        elevation_str = item.find('p').text.split(': ')[1]
        elevation = int(re.sub(r'[^\d]', '', elevation_str))
        
        # Extract the temperature and convert it to an integer
        temperature_str = item.find('div', class_='weather-value').text.strip()
        temperature = int(temperature_str)  # Convert to integer

        # Create a dictionary for each weather entry
        weather_entry = {
            'location': location,
            'elevation': elevation,
            'temperature': f"{temperature}"
        }
        
        # Append the entry to the weather_data list
        weather_data.append(weather_entry)    
    
    # Pass the content to the template
    context = {
        'sunpeaks_weather': weather_data
    }
    return render(request, 'index.html', context)
