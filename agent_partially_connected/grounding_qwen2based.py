import sys , os


import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation import GenerationConfig
from peft import AutoPeftModelForCausalLM
import ast
import json
import re
import argparse
import os
from PIL import Image
import logging
from tqdm import tqdm
from lsq.utils import pred_2_point
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from prompts import *

logging.basicConfig(level=logging.INFO)

class GroundingQwen2Based:
    def __init__(self, qwen_path, model_path, range1000=False):
        self.qwen_path = qwen_path
        self.model_path = model_path
        self.range1000 = range1000
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(model_path, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
        self.processor = AutoProcessor.from_pretrained(qwen_path)
        self.model.generation_config = GenerationConfig.from_pretrained(qwen_path, trust_remote_code=True)


    def get_click_point(self, img_path, instruction):
        prompt = USR_GROUNDING.format(instruction)
        messages = [
        {
            "role": "system",
            "content": SYS_GROUNDING
        },
        {
            "role": "user",
            "content": [
                {'image': img_path},
                {'text': prompt}
            ],
        }]
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to("cuda")
        generated_ids = self.model.generate(**inputs, max_new_tokens=1000)
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        click_point = pred_2_point(output_text)
        if self.range1000:
            click_point = [item / 1000 for item in click_point]
        return click_point




# need to adjust to screenspot?
# min_pixels = 256*28*28
# max_pixels = 1344*28*28










