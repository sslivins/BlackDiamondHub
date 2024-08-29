from django.shortcuts import render
import requests
from bs4 import BeautifulSoup
from django.shortcuts import render

def landing_page(request):
    url = 'https://www.sunpeaksresort.com/bike-hike/weather-webcams/weather'  # Replace with the URL you want to fetch
    response = requests.get(url)
    
    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract specific content
    content = soup.find('div', {'class': 'weather current-conditions'})  # Adjust as needed
    
    # Pass the content to the template
    context = {
        'external_content': str(content)
    }
    return render(request, 'index.html', context)
