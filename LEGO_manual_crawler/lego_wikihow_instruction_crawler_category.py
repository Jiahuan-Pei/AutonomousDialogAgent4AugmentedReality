"""
    This script:
        crawls multimodal wikihow manuals from https://www.wikihow.com by category.
        generates texts and images, respectively.
    We crawled xxx manuals in total.

    Submit:
        cd ~/ARTA/LEGO_manual_crawler
        nohup python lego_wikihow_instruction_crawler_category.py > wikihow.output.log 2>&1 &
    Check:
        ps aux | grep "lego_wikihow_instruction_crawler_category.py"
    Kill:
        kill -9 #NUMBER
"""

import time
import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, parse_qs, unquote
import re
from tqdm import tqdm
import json
import numpy as np


# Define the URL of the website to crawl
base_url = f"https://www.wikihow.com"
resource_prefix = 'wikihow'

base_data_dir = '/media/PampusData/jpei'
dataset_name = 'vox_arta_dataset'
# Define the directory where you want to save the downloaded resources
base_manual_dir = os.path.join(base_data_dir, dataset_name, "manuals", resource_prefix)  # /media/PampusData/jpei/vox_arta_dataset/manuals/lego
os.makedirs(base_manual_dir, exist_ok=True)

category_prefix = '/Category:'

# 302 + 10 LEGO + 36 Furniture Assembly
# category_list = [
#     'Crafts',   #  84
#     'Recipes',  #  37
#     'Games',    # 102
#     'Cars'      #  79
# ]


def get_all_categories():
    url = 'https://www.wikihow.com/Special:CategoryListing#AllCategories'
    # Send an HTTP GET request to the resource URL
    resource_response = requests.get(url)
    if resource_response.status_code == 200:
        html = resource_response.content
        soup = BeautifulSoup(html, 'html.parser')
        # soup.find_all('div', attrs={'id', 'catlist'})
        category_list = [a.get('href') for a in soup.find_all('a')]
        category_list = [a for a in category_list if a and a.startswith('/Category:')]  # 135
    return category_list


def download_image_or_video(img_url, image_dir):
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


def download_resource(url, category_manual_dir):

    doc_name = os.path.basename(url)
    doc_dir = os.path.join(category_manual_dir, doc_name)
    image_dir = os.path.join(doc_dir, 'images')

    # Send an HTTP GET request to the resource URL
    resource_response = requests.get(url)
    # Check if the request was successful (status code 200)
    if resource_response.status_code == 200:
        html = resource_response.content
        soup = BeautifulSoup(html, 'html.parser')

        section_elements = soup.select('[class^="section steps"]')

        steps = [[r.select('[id^="step-id-"]') for r in element.select('[id^="steps_"]')] for element in section_elements]

        num_section_elements = len(steps[0])

        if num_section_elements:
            os.makedirs(doc_dir, exist_ok=True)
            os.makedirs(image_dir, exist_ok=True)
        else:
            print(f'Skip without steps: {url}')
            return

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
        filename = os.path.join(category_manual_dir, doc_name, f"{doc_name}.html")
        with open(filename, 'w', encoding="utf-8") as f:
            f.write(updated_html)
        print(f"Downloaded: {filename}\t\t[{url}]")

        list_of_url_list = []
        for element in section_elements:
            url_list = []
            for s in element.find_all('div', 'content-spacer'):
                try:
                    v = s.find('video')
                    if v:
                        url = f"{base_url}/video{v.get('data-src')}"
                    else:
                        url = s.find('img').get('src')
                    # Download image or video
                    download_image_or_video(url, image_dir)
                    url_list.append(url)
                except:
                    pass
            list_of_url_list.append(url_list)

        summary = soup.find('div', 'mf-section-0').get_text().strip()

        if num_section_elements == 1:
            section_id_list = ['1']
            section_head_list = ['']

            list_of_step_list = [[[re.sub('\n+', '\n', s.get_text().strip()) for s in element.find_all('div', 'step')][0] for element in section_elements]]
            list_of_step_num_list = [[
                r.select_one('[id^="step-id-"] a')['name'].split('_')[1]
                for element in section_elements
                for r in element.select('[id^="steps_"]')
            ]]

            # list_of_url_list = [d[0] for d in list_of_url_list]
        else:
            section_id_list = [element.find('div', 'altblock').get_text().strip() for element in section_elements] # Either 'Part #NUMBER' or 'Method #NUMBER' or '#NUMBER (tips)'
            section_head_list = [element.find('span', 'mw-headline').get_text().strip() for element in section_elements]

            list_of_step_list = [[re.sub('\n+', '\n', s.get_text().strip()) for s in element.find_all('div', 'step')] for element in section_elements]
            list_of_step_num_list = [[s.get_text().strip() for s in element.find_all('div', 'step_num')] for element in section_elements]

        try:
            thingsyoushouldknow = [r.get_text().strip() for r in soup.find('div', attrs={'id': 'thingsyoushouldknow'}).find_all('li')]
        except:
            thingsyoushouldknow = []

        try:
            ingredients = [r.get_text().strip() for r in soup.find('div', attrs={'id': 'ingredients'}).find_all('li')]
        except:
            ingredients = []

        try:
            tips = [t.div.get_text().strip() for t in soup.find('div', attrs={'id': 'tips'}).find_all('li')]
        except:
            tips = []

        try:
            warnings = [t.div.get_text().strip() for t in soup.find('div', attrs={'id': 'warnings'}).find_all('li')]
        except:
            warnings = []

        try:
            qa_pairs = [{'question': t.find('div', 'qa_q_txt').get_text().strip(), 'answer': t.find('div', 'qa_answer answer').get_text().strip()} for t in soup.find('div', attrs={'id': 'qa'}).find_all('div', 'qa_li_container')]
        except:
            qa_pairs = []

        with open(os.path.join(category_manual_dir, doc_name, f'{doc_name}.json'), 'w') as fw:
            json_manual = {
                'manual_id': doc_name,
                'manual_type': 'wikihow',
                'summary': summary,
                'thingsyoushouldknow': thingsyoushouldknow,
                'ingredients': ingredients,
                'sections': [
                                {
                                    'section_id': section_id,
                                    'section_name': section_name,
                                    'steps': [
                                        {
                                            'step_id': step_id,
                                            'step_instruction': step_instruction,
                                            'step_img_url': img_url
                                        } for step_id, step_instruction, img_url in zip(list_of_step_num_list[i], list_of_step_list[i], list_of_url_list[i])
                                    ]
                                } for i, (section_id, section_name) in enumerate(zip(section_id_list, section_head_list))
                ],
                'tips': tips,
                'warnings': warnings,
                'qa_pairs': qa_pairs,
                'url': f'{base_url}/{doc_name}',
            }

            json.dump(json_manual, fw)

        time.sleep(2)
    else:
        print(f"Failed to download: {url}")


def extract_wikihow_instruction_from_page(url, category_manual_dir, count_crawled_doc=0):

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
                    download_resource(href, category_manual_dir)  # DOWNLOAD raw webpage here.
                    count_crawled_doc += 1
                    print(f"count_crawled_doc={count_crawled_doc};")
            except:
                print(f'Download Error!!!{href}')
    else:
        print(f"Failed to retrieve the web page: {url}")


if __name__ == "__main__":
    category_list = get_all_categories()#[:1]

    instruction_len_dict = {}

    for category in category_list:
        # Start by extracting resources from the initial page
        instruction_len_dict[category] = []
        category_manual_dir = os.path.join(base_manual_dir, category.replace(category_prefix, ''))
        os.makedirs(category_manual_dir, exist_ok=True)
        extract_wikihow_instruction_from_page(f"{base_url}{category}", category_manual_dir=category_manual_dir)
        instruction_len_dict[category] = np.mean(instruction_len_dict[category])

    print(instruction_len_dict)


