from bs4 import BeautifulSoup
import json
import os
import requests

def download_images_to_subfolder(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    instructions = json_data.get("instructions", [])
                    for instruction in instructions:
                        img_url = instruction.get('img_url')
                        if img_url:
                            try:
                                response = requests.get(img_url)
                                if response.status_code == 200:
                                    images_folder = os.path.join(root, 'images')
                                    if not os.path.exists(images_folder):
                                        os.makedirs(images_folder)
                                    img_name = os.path.basename(img_url)
                                    save_path = os.path.join(images_folder, img_name)
                                    with open(save_path, 'wb') as img_file:
                                        img_file.write(response.content)
                                    print(f"Downloaded {img_url} to {save_path}")
                            except requests.RequestException as e:
                                print(f"Error downloading {img_url}: {e}")

def make_new_json(folder_path,fn):
    with open(folder_path + '/' + fn + '/' + fn + '.html', 'r', encoding='utf-8') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'lxml')
    rows = soup.find_all(class_='row')
    #     print(soup)

    data = []
    snellius_dir = 'change' + fn + '/images/'# change it to your path
    instruction_id = 0
    for row in rows:
        #     row_data = {'instruction_id': instruction_id}
        row_data = {
            'instruction_id': instruction_id,
            'text': 'None',
            'VLM': {
                'img_path': 'change', # change it to your path
                'task_label': 'None',
                'query': 'None',
                'MiniGPTv2_output': 'None'
            }
        }

        img = row.find(class_='image').find('img')
        row_data['img'] = img['src'].replace("./LEGO 60274 Elite Police Lighthouse Capture_files/",
                                             "https://legoaudioinstructions.com/wp-content/themes/mtt-wordpress-theme/assets/manual/manual-images/60274/").replace(
            "#", "%23").replace(" ", "%20") if img and img.has_attr('src') else 'No image found'
        #         print(row_data['img'])
        # print(row_data['img'])
        if row_data['img'] != 'No image found':
            row_data['VLM']['img_path'] = snellius_dir + img['src'].split('/')[-1].replace("#", "%23").replace(" ",
                                                                                                               "%20").replace(
                "./LEGO 60274 Elite Police Lighthouse Capture_files/https://legoaudioinstructions.com/wp-content/themes/mtt-wordpress-theme/assets/manual/manual-images/60274/",
                "%20")

        #         print(row_data['VLM']['img_path'])
        text = row.find(class_='text')
        #     print(text.find_all(class_='txtbox'))
        if text:

            txtboxes = text.find_all(class_='txtbox')
            row_data['text'] = [txtbox.text.strip() for txtbox in txtboxes]
            row_data['entities'] = []
            query_texts = []
            for txtbox in txtboxes:
                txtbox_data = [{child['class'][0] if child.has_attr('class') else 'this_line': child.text.strip()} for
                               child in txtbox.find_all()]
                row_data['entities'].append(txtbox_data)
                query_texts.extend([child.text.strip() for child in txtbox.find_all() if
                                    child.has_attr('class') and child['class'][0] != 'verb'])

            for line in row_data['entities']:
                if len(line) > 1:
                    if 'verb' in line[1]:
                        if line[1]['verb'] == 'Collect':
                            row_data['VLM']['task_label'] = '[detection-collect]'
                            row_data['VLM']['query'] = 'Collect ' + ' '.join(query_texts)
                            break
                        elif line[1]['verb'] == 'Find':
                            row_data['VLM']['task_label'] = '[detection]'
                            #                         print(line[0]['this_line'])
                            row_data['VLM']['query'] = ''.join(line[0]['this_line'])
                            break
        else:
            row_data['text'] = 'No text found'

        data.append(row_data)

        instruction_id += 1
    whole_json = {
        "manual_id": fn,
        "manual_type": "lego",
        "instructions": data
    }

    json_data = json.dumps(whole_json, indent=4, ensure_ascii=False)
    folder_name = 'json_file'
    os.makedirs(folder_name, exist_ok=True)
    with open('json_file/' + fn + '.json', 'w', encoding='utf-8') as json_file:
        json_file.write(json_data)





def main():
    
    lego_folder_path = 'ARTA_LEGO/lego' # change it to your html files path
    for entry in os.listdir(lego_folder_path):
        full_path = os.path.join(lego_folder_path, entry)
        if os.path.isdir(full_path):
            make_new_json( lego_folder_path,entry)
    download_images_to_subfolder(lego_folder_path)



if __name__ == '__main__':
    main()