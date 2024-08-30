from django.shortcuts import render
import requests
from requests.exceptions import RequestException
from django.http import HttpResponse
from bs4 import BeautifulSoup

def landing_page(request):
    url = 'https://www.sunpeaksresort.com/bike-hike/weather-webcams/weather'  # Replace with the URL you want to fetch
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract the current weather
        content = soup.find('div', {'class': 'weather current-conditions'})  # Adjust as needed        
    except RequestException as e:
        print(f"Failed to fetch content from {url}")
        content = "Error Loading Weather"
    
    # Pass the content to the template
    context = {
        'external_content': str(content)
    }
    return render(request, 'index.html', context)
