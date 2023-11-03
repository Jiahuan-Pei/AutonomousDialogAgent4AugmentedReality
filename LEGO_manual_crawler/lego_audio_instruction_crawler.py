import requests
from bs4 import BeautifulSoup
import os

# Define the URL of the website to crawl
base_url = "https://legoaudioinstructions.com/instructions/"

# Define the directory where you want to save the downloaded resources
output_directory = "lego_instructions"

# Create the output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)


def download_resource(url, output_directory):
    # Send an HTTP GET request to the resource URL
    resource_response = requests.get(url)

    # Check if the request was successful (status code 200)
    if resource_response.status_code == 200:
        # Save the resource to the local file
        filename = os.path.join(output_directory, os.path.basename(url))
        with open(filename, 'wb') as f:
            f.write(resource_response.content)
        print(f"Downloaded: {filename}")
    else:
        print(f"Failed to download: {url}")


def extract_resources_from_page(url, output_directory):
    # Send an HTTP GET request to the page
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all links on the page
        links = soup.find_all('a', class_='mtt-instruction-card')

        # Loop through the links and download resources
        for link in links:
            href = link.get('href')
            if href:
                # Check if the link leads to a downloadable resource (e.g., a PDF, ZIP, etc.)
                # Send an HTTP GET request to the linked webpage
                linked_page_response = requests.get(href)
                soup2 = BeautifulSoup(linked_page_response.text, 'html.parser')
                page_url = soup2.find('a', class='button icon')
                download_resource(page_url)


        # Find the link to the next page, if it exists
        next_page_link = soup.find('a', text='Next')
        if next_page_link:
            next_page_url = base_url + next_page_link.get('href')
            # Recursively extract resources from the next page
            extract_resources_from_page(next_page_url, output_directory)

    else:
        print(f"Failed to retrieve the web page: {url}")


# Start by extracting resources from the initial page
extract_resources_from_page(base_url, output_directory)
