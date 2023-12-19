"""
    This script:
        crawls multimodal lego manuals from https://legoaudioinstructions.com/instructions/.
        generates texts and images, respectively.
    We crawled xxx manuals in total.
"""

import time
import requests
import os
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import numpy as np


# Define the URL of the website to crawl
base_url = "https://legoaudioinstructions.com/instructions/"
base_data_dir = '/media/Blue2TB3/jpei'
dataset_name = 'vox_arta_dataset'
resource_prefix = 'lego'
base_manual_dir = os.path.join(base_data_dir, dataset_name, "manuals", resource_prefix)  # /media/PampusData/jpei/vox_arta_dataset/manuals/lego
os.makedirs(base_manual_dir, exist_ok=True)


def download_image(img_url, image_dir):
    # Send an HTTP GET request to the image URL
    image_response = requests.get(img_url)

    # Check if the request was successful (status code 200)
    if image_response.status_code == 200:
        # Get the image's filename from the URL
        filename = os.path.join(image_dir, os.path.basename(img_url))

        # Save the image to the local file
        with open(filename, 'wb') as f:
            f.write(image_response.content)
    return 


def download_resource(url, base_manual_dir, folder_name=None):
    # Save the resource to the local folder
    folder_dir = os.path.join(base_manual_dir, f"{folder_name}")
    image_dir = os.path.join(folder_dir, "images")

    if os.path.exists(folder_dir):
        print(f"Downloaded before: {folder_dir}\t\t[{url}]")
        return
    else:
        os.makedirs(folder_dir, exist_ok=True)
        os.makedirs(image_dir, exist_ok=True)

        # Send an HTTP GET request to the resource URL
        resource_response = requests.get(url)

        # Check if the request was successful (status code 200)
        if resource_response.status_code == 200:
            # Download the raw webpage
            with open(os.path.join(folder_dir, f'{folder_name}.html'), 'wb') as f:
                f.write(resource_response.content)
            print(f"Downloaded: {folder_dir}\t\t[{url}]")

            # Parse the HTML content of the page and download images
            soup = BeautifulSoup(resource_response.text, 'html.parser')

            # Find all image tags in the manual-table-container and Download and save each image
            img_urls = [img_tag.get('src') for img_tag in soup.find('div', class_='manual-table-container').find_all('img')]
            for img_url in tqdm(img_urls):
                if img_url:
                    download_image(img_url, image_dir=image_dir)

            # Find all textual instructions and save json
            # text_list = [r.get_text().strip() for r in soup.find('div', class_='manual-table-container').find_all('div', 'row')]
            text_list = [r.get_text().strip() for r in soup.find('div', class_='manual-table-container').find_all('td')]
            print(text_list)
            with open(os.path.join(folder_dir, f'{folder_name}.json'), 'w') as fw:
                json_manual = {
                    'manual_id': folder_name,
                    'manual_type': 'lego',
                    'instructions': [
                        {
                            'instruction_id': instruction_id,
                            'text': text,
                            'img_url': img_url
                        } for instruction_id, (text, img_url) in enumerate(zip(text_list, img_urls))
                    ]
                }
                json.dump(json_manual, fw)

            time.sleep(2)
        else:
            print(f"Failed to download: {url}")
        return len(text_list)


def extract_resources_from_page(url, output_dir, pagenumber=0, count_crawled_doc=0):
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
                folder_name = os.path.basename(page_url.strip('/'))     # E.g., 'lego-31130-c-sunken-treasure-mission-readscr'
                instruction_len = download_resource(page_url, output_dir, folder_name=f"{folder_name}")
                instruction_len_list.append(instruction_len)

        # Find the link to the next page, if it exists
        try:
            has_next_page = soup.find('li', class_="next").a.get('class')
            if has_next_page != 'disabled' and pagenumber<7:
                pagenumber += 1
                next_page_url = base_url + f'?pagenumber={pagenumber}'

                # Recursively extract resources from the next page
                extract_resources_from_page(next_page_url, output_dir, pagenumber, count_crawled_doc)
        except:
            pass

    else:
        print(f"Failed to retrieve the web page: {url}")


if __name__ == "__main__":
    # Start by extracting resources from the initial page
    instruction_len_list = []
    extract_resources_from_page(base_url, base_manual_dir)
    print(np.mean(instruction_len_list))

    # Download again if missing
    # download_resource(url='https://legoaudioinstructions.com/'+'lego-60274-elite-police-lighthouse-capture-mobile', base_manual_dir='/media/Blue2TB3/jpei/vox_arta_dataset/manuals/lego', folder_name='lego-60274-elite-police-lighthouse-capture-mobile')
