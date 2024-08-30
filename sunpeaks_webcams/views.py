from django.shortcuts import render
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urlunsplit, parse_qs

# Create your views here.
def webcams(request):
    url = 'https://www.sunpeaksresort.com/bike-hike/weather-webcams/webcams'  # Replace with the URL you want to fetch
    domain = 'https://www.sunpeaksresort.com'
    response = requests.get(url)
    
    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract specific content
    content = soup.find('div', {'id': 'webcams'})
    
    # Collect image timestamps
    image_timestamps = {}    
  
    if content:
        # Iterate over all img tags within the content
        for img_tag in content.find_all('img'):
            # Prepend the domain to relative image paths
            if img_tag['src'].startswith('/'):
                img_tag['src'] = domain + img_tag['src']
                
            if 'timestamp=' in img_tag['src']:
              split_url = urlsplit(img_tag['src'])
              base_url = urlunsplit((split_url.scheme, split_url.netloc, split_url.path, '', ''))
              query_params = parse_qs(split_url.query)
              timestamp = query_params.get("timestamp", [None])[0]
              image_timestamps[base_url] = timestamp
                
    context = {
        'external_webcams': str(content),
        'image_timestamps': image_timestamps,
    }
    return render(request, 'webcams.html', context)