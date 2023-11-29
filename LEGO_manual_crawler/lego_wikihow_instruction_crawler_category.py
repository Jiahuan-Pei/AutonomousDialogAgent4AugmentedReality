import time
import requests
import os

from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, parse_qs, unquote
import re

# 302 + 10 LEGO + 36 Furniture Assembly
category_list = [
    'Crafts',   #  84
    'Recipes'   #  37
    'Games',    # 102
    'Cars'      #  79
    ]

# Define the URL of the website to crawl
base_url = f"https://www.wikihow.com"

resource_prefix = 'wikihow'


# Define the directory where you want to save the downloaded resources
output_directory = os.path.join(os.path.dirname(os.getcwd()), "manuals")
# Create the output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)


def download_resource(url, output_directory, prefix="", doc_id="", doc_name=""):
    # Send an HTTP GET request to the resource URL
    resource_response = requests.get(url)

    # Check if the request was successful (status code 200)
    if resource_response.status_code == 200:
        html = resource_response.content
        soup = BeautifulSoup(html, 'html.parser')

        # Find the <img> element
        # Assign the real sources of images
        img_tags = soup.find_all('img')
        for img_tag in img_tags:
            # Get the value of the 'data-src' attribute
            src_value = img_tag.get('src')
            data_src_value = img_tag.get('data-src')

            # Assign the 'data-src' value to the 'src' attribute
            if src_value is None:
                if data_src_value:
                    # Create a new <img> element with only the 'src' attribute
                    new_img_tag = soup.new_tag('img', src=data_src_value)

                    # Replace the original <img> element with the new one
                    img_tag.replace_with(new_img_tag)
                else:
                    # print(f'Do not have the source of images, so we ignore...{doc_name}')
                    print(f'IMAGE ERROR:{img_tag}')
            else:
                pass

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


def extract_wikihow_instruction_from_page(url, category, output_directory, count_crawled_doc=0):

    # Send an HTTP GET request to the page
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all links on the page
        links = soup.find_all('div', class_='content')[0].find_all('a')

        # Loop through the links and download resources
        for link in links:
            href = link.get('href')
            try:
                if href and href.startswith('https'):
                    doc_name = unquote(urlparse(href).path[1:])
                    download_resource(href, output_directory, prefix=f"{resource_prefix}_{category.lower()}_", doc_name=f"{doc_name}.html")  # DOWNLOAD raw webpage here.
                    count_crawled_doc += 1
                    print(f"count_crawled_doc={count_crawled_doc};")
            except:
                print(f'Download Error!!!{doc_name}')
    else:
        print(f"Failed to retrieve the web page: {url}")


if __name__ == "__main__":
    for category in category_list:
        # Start by extracting resources from the initial page
        extract_wikihow_instruction_from_page(f"{base_url}/Category:{category}", category=category, output_directory=output_directory)

