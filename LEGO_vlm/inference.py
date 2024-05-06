import argparse
import os
import random
import sys
import numpy as np
import torch
import torch.backends.cudnn as cudnn
import glob

from minigpt4.common.config import Config
from minigpt4.common.dist_utils import get_rank
from minigpt4.common.registry import registry
# from minigpt4.conversation.conversation import Chat, Conversation
from minigpt4.conversation.conversation import Conversation, SeparatorStyle, Chat

from minigpt4.datasets.builders import *
from minigpt4.models import *
from minigpt4.processors import *
from minigpt4.runners import *
from minigpt4.tasks import *
import json
import logging
logging.basicConfig(level=logging.INFO, filename='output.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')



def parse_args():
    parser = argparse.ArgumentParser(description="Demo")
    parser.add_argument("--cfg-path", default='minigptv2_eval.yaml', help="path to configuration file.")
    parser.add_argument("--gpu-id", type=int, default=0, help="specify the gpu to load the model.")
    parser.add_argument("--num-beams", type=int, default=1, help="specify the gpu to load the model.")
    parser.add_argument("--temperature", type=int, default=0.6, help="specify the gpu to load the model.")
    parser.add_argument("--prompt", type=str, default="",
                        help="")
    parser.add_argument("--answer-txt", type=str,
                        default="/gpfs/home4/hhuang/MiniGPT/MiniGPT-4/answer.txt")
    parser.add_argument(
        "--options",
        nargs="+",
        help="override some settings in the used config, the key-value pair "
             "in xxx=yyy format will be merged into config file (deprecate), "
             "change to --cfg-options instead.",
    )
    args = parser.parse_args()
    return args


def setup_seeds(config):
    seed = config.run_cfg.seed + get_rank()
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    cudnn.benchmark = False
    cudnn.deterministic = True


# ========================================
#             Model Initialization
# ========================================
CONV_VISION_minigptv2 = Conversation(
    system="Give the following image: <Img>ImageContent</Img>. "
           "You will be able to see the image once I provide it to you, Please answer my questions.",
    roles=("<s>[INST] ", " [/INST]"),
    messages=[],
    offset=2,
    sep_style=SeparatorStyle.SINGLE,
    sep="",
)

print('Initializing Chat')
args = parse_args()
cfg = Config(args)

model_config = cfg.model_cfg
model_config.device_8bit = args.gpu_id
model_cls = registry.get_model_class(model_config.arch)
model = model_cls.from_config(model_config).to('cuda:{}'.format(args.gpu_id))

vis_processor_cfg = cfg.datasets_cfg.cc_sbu_align.vis_processor.train
vis_processor = registry.get_processor_class(vis_processor_cfg.name).from_config(vis_processor_cfg)
chat = Chat(model, vis_processor, device='cuda:{}'.format(args.gpu_id))
print('Initialization Finished')


def single_inference(img_path, this_query):
    image_path = img_path
    chat_state = CONV_VISION_minigptv2.copy()
    img_list = []
    img_list2 = []
    chat.upload_img(image_path, chat_state, img_list)
    img_list2.append(img_list)
    txt_path = args.answer_txt
    query = this_query
    chat.ask(query, chat_state)
    chat.encode_img(img_list2[-1])
    llm_message = chat.answer(
        conv=chat_state,
        img_list=img_list2[-1],
        num_beams=args.num_beams,
        temperature=args.temperature,
        max_new_tokens=500,
        max_length=2000
    )[0]
    return llm_message

done_list=[]


def create_this_conv(model_name,the_id, image_path, query, answer):
    data_entry = {
        "id": the_id,
        "image": image_path,
        "conversations": [
            {
                "from": "human",
                "value": query},
            {
                "from": model_name,
                "value": answer}]
    }
    # temp_json.append(data_entry)
    #         print(temp_json[0])
    return data_entry


def detection_inference(input_folder):
    for file_name in os.listdir(input_folder):
        if file_name.endswith('.json') and file_name == 'lego-60274-elite-police-lighthouse-capture-mobile_new.json':  
            with open(os.path.join(input_folder, file_name), 'r', encoding='utf-8') as file:
                json_data = json.load(file)
                data = json_data["instructions"]


            for instruction in data:
                if 'VLM' in instruction and instruction['VLM']['task_label'] == '[detection]':
                    query = '[detection]' + instruction['VLM'].get('query', 'No Query')
                    img_path = instruction['VLM'].get('img_path', 'No Image Path')
                    answer = single_inference(img_path, query)
                    instruction['VLM']['answer'] = answer

            with open(os.path.join(input_folder, file_name), 'w', encoding='utf-8') as file:
                json.dump(json_data, file, ensure_ascii=False, indent=4)

detection_inference('change') #your json path

