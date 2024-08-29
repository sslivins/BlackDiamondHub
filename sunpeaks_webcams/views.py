from django.shortcuts import render
import requests
from bs4 import BeautifulSoup
from django.shortcuts import render

# Create your views here.
def webcams(request):
    print("Fetching webcams...")
    url = 'https://www.sunpeaksresort.com/bike-hike/weather-webcams/webcams'  # Replace with the URL you want to fetch
    domain = 'https://www.sunpeaksresort.com'
    response = requests.get(url)
    
    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract specific content
    content = soup.find('div', {'id': 'webcams'})
    
    if content:
        # Iterate over all img tags within the content
        for img_tag in content.find_all('img'):
            # Prepend the domain to relative image paths
            if img_tag['src'].startswith('/'):
                img_tag['src'] = domain + img_tag['src']    
    
    context = {
        'external_webcams': str(content)
    }
    return render(request, 'webcams.html', context)