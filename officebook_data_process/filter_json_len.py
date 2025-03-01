import os
from typing import List

from tqdm import tqdm

import torch
from transformers import Qwen2VLForConditionalGeneration
from qwen_vl_utils import process_vision_info
from peft import AutoPeftModelForCausalLM
from transformers.generation import GenerationConfig
from transformers import AutoModelForCausalLM, AutoProcessor
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

from openai import OpenAI
import base64
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import json
import copy


def calc(processor: AutoProcessor, messages: List[dict]):
    print(messages)
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    return inputs["input_ids"].shape[1]

# 加载 qwen2vl 的 tokenizer 和 processor（假设是多模态模型）
processor = AutoProcessor.from_pretrained("osunlp/UGround-V1-7B")




with open('/Users/lianshuquan/github_repo/agent_partially_connected/officebook_data.json') as file:
    data = json.load(file)

new_data = []
for item in data:

    messages = copy.deepcopy(item['messages'])
    messages[1]['content'] = [
        {'type': 'text', 'text': messages[1]['content']}
    ]
    for img_path in item['images']:
        messages[1]['content'].append({'type': 'image', 'image': img_path})
    token_len = calc(processor, messages)
    
    if token_len > 2300:
        print(token_len)
        print('----------------------')
    else:
        new_data.append(item)

with open('officebook_data_filtered.json', 'w') as file:
    json.dump(new_data, file, indent=2, ensure_ascii=False)
