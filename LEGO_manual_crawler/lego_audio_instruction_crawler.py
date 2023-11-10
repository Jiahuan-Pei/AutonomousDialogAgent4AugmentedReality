import time
import requests
import os
from bs4 import BeautifulSoup


# Define the URL of the website to crawl
base_url = "https://legoaudioinstructions.com/instructions/"

# Define the directory where you want to save the downloaded resources
# output_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instructions")
output_directory = os.path.join(os.path.dirname(os.getcwd()), "instructions") # Parent dir of the current working dir

# Create the output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)


def download_resource(url, output_directory, doc_name=None):
    # Save the resource to the local file
    filename = os.path.join(output_directory, f"{doc_name}")
    if os.path.exists(filename):
        print(f"Downloaded before: {filename}\t\t[{url}]")
        return

    # Send an HTTP GET request to the resource URL
    resource_response = requests.get(url)

    # Check if the request was successful (status code 200)
    if resource_response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(resource_response.content)
        print(f"Downloaded: {filename}\t\t[{url}]")
        time.sleep(2)
    else:
        print(f"Failed to download: {url}")


def extract_resources_from_page(url, output_directory, pagenumber=0, count_crawled_doc=0):
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
                page_url = soup2.find_all('a', class_='button icon')[0].get('href')
                count_crawled_doc += 1
                print(f"count_crawled_doc={count_crawled_doc}")
                download_resource(page_url, output_directory, doc_name=f"{page_url.split('/')[-2]}.html")



        # Find the link to the next page, if it exists
        try:
            has_next_page = soup.find('li', class_="next").a.get('class')
            if has_next_page != 'disabled':
                pagenumber += 1
                next_page_url = base_url + f'?pagenumber={pagenumber}'

                # Recursively extract resources from the next page
                extract_resources_from_page(next_page_url, output_directory, pagenumber,count_crawled_doc)
        except:
            pass

    else:
        print(f"Failed to retrieve the web page: {url}")


if __name__ == "__main__":
    # Start by extracting resources from the initial page
    extract_resources_from_page(base_url, output_directory)
