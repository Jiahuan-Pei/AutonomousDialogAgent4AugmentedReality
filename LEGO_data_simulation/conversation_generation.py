import os
from bs4 import BeautifulSoup
import re
import json

def lego_manual_parser(file_name, file_dir):
    # Open the HTML file
    with open(os.path.join(file_dir, file_name), 'r', encoding='utf-8') as file:
        # Read the content of the file
        html_content = file.read()
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    text_image_guidelins = soup.find_all('div', 'row')
    cleaned_text_guidelines = [re.sub(r'\n+', '\n', r.get_text().strip()) for r in soup.find_all('div', 'row')]
    return '\n\n'.join(cleaned_text_guidelines)


def conversation_generation_main():
    manual_dir = '../manuals'

    import re
    from tqdm.notebook import tqdm

    count = 0
    for file_name in tqdm(os.listdir(manual_dir)):
        try:
            if file_name.startswith('lego'):
                lego_manual_parser(file_name, manual_dir)

        except:
            print(f'Error: {file_name}')

if __name__ == '__main__':
    conversation_generation_main()