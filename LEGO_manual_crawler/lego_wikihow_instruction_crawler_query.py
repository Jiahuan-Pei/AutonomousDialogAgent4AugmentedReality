import time
import requests
import os

from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, parse_qs
import re

# Define the URL of the website to crawl
base_url = f"https://www.wikihow.com"
search_url = f"{base_url}/wikiHowTo"

query_prefix = 'How to'
# doc_prefix = 'wikihow'
doc_prefix = 'wikihow_assembly'

# query_object = 'LEGO'
seed_object = 'furniture'

seed_queries = [f'{query_prefix} make a {seed_object}', f'{query_prefix} build a {seed_object}', f'{query_prefix} assemble a {seed_object}']

# Define the directory where you want to save the downloaded resources
output_directory = os.path.join(os.path.dirname(os.getcwd()), "manuals")
# Create the output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)


def download_resource(url, output_directory, prefix=None, doc_id=None, doc_name=None):
    # Send an HTTP GET request to the resource URL
    resource_response = requests.get(url)

    # Check if the request was successful (status code 200)
    if resource_response.status_code == 200:
        html = resource_response.content
        soup = BeautifulSoup(html, 'html.parser')
        # Find the <img> element
        img_tags = soup.find_all('img')

        # Assign the real sources of images
        for img_tag in img_tags:
            # Get the value of the 'data-src' attribute
            data_src_value = img_tag.get('data-src')

            # Assign the 'data-src' value to the 'src' attribute
            if data_src_value:
                # Create a new <img> element with only the 'src' attribute
                new_img_tag = soup.new_tag('img', src=data_src_value)

                # Replace the original <img> element with the new one
                img_tag.replace_with(new_img_tag)

        # Get the updated HTML content as a string
        updated_html = str(soup)
        # Save the resource to the local file
        filename = os.path.join(output_directory, f"{prefix}{doc_id}{doc_name}")
        with open(filename, 'w', encoding="utf-8") as f:
            f.write(updated_html)
        print(f"Downloaded: {filename}\t\t[{url}]")
        time.sleep(2)
    else:
        print(f"Failed to download: {url}")


def extract_wikihow_instruction_from_page(url, output_directory, start=0, count_no_match=0, count_crawled_doc=0):

    # Send an HTTP GET request to the page
    response = requests.get(url)
    search_value = parse_qs(urlparse(url).query).get('search', [''])[0] # With 'How to'

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all links on the page
        links = soup.find_all('a', class_='result_link')

        # Loop through the links and download resources
        for link in links:
            href = link.get('href')
            if href:
                # Craw metadata
                # Find the form element by its ID
                metadata_form = link.find('form', id='sherlock-form')

                if metadata_form:
                    # Extract data from the form
                    sha_id = metadata_form.find('input', {'name': 'sha_id'})['value']
                    sha_title = metadata_form.find('input', {'name': 'sha_title'})['value']

                    # Print the extracted data
                    print("sha_id:", sha_id)
                    print("sha_title:", sha_title) # Without 'How to'
                    print(f"url:{href}")
                else:
                    print("Form with the specified ID not found on the page.")

                # Parse the search value
                # retrieved_parsed_query = href.split('/')[-1].replace('-', ' ')
                retrieved_parsed_query = f"{query_prefix} {sha_title.replace('-', ' ')}"
                # Double check the seed object exist
                if seed_object in retrieved_parsed_query.lower():
                    print(f"count_crawled_doc={count_crawled_doc}; count_no_match={count_no_match}")
                    download_resource(href, output_directory, prefix=f"{doc_prefix}_", doc_id=f"{sha_id}_",
                                      doc_name=f"{href.split('/')[-1]}.html")  # DOWNLOAD raw webpage here.
                    count_crawled_doc += 1
                else:
                    count_no_match += 1
                    continue

            if count_no_match >= 2*num_instruction_display:
                print('Cannot find matched doc in the next two pages.')
                exit()


        # Find the link to the next page, if it exists
        has_no_next_page = soup.find('span', class_='button buttonleft primary disabled')
        if has_no_next_page:
            start += num_instruction_display
            encoded_query = urlencode({'search': search_value, 'start': start})
            next_page_url = f'{search_url}?{encoded_query}'

            # Recursively extract resources from the next page
            extract_wikihow_instruction_from_page(next_page_url, output_directory, start, count_no_match, count_crawled_doc)

    else:
        print(f"Failed to retrieve the web page: {url}")


if __name__ == "__main__":
    num_instruction_display = 15
    for q in seed_queries:
        encoded_query = urlencode({'search': q})
        # Start by extracting resources from the initial page
        extract_wikihow_instruction_from_page(f"{search_url}?{encoded_query}", output_directory)

