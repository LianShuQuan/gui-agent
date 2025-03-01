from typing import List
from openai import OpenAI
from prompts import *
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from utils import *
import torch

import logging

from excutor import *



class Agent:
    def __init__(self, local: bool=False, 
                 llm_model: str=None, llm_api_key: str=None, llm_api_base: str=None,
                 qwen_path: str=None, model_path: str=None):
        self.history = []
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.llm_api_base = llm_api_base
        self.local = local

        if not local:
            # openai client
            self.client = OpenAI(api_key=self.llm_api_key, base_url=self.llm_api_base)
        else:
            # local model only support qwen2based
            self.processor = AutoProcessor.from_pretrained(qwen_path)

            self.model = Qwen2VLForConditionalGeneration.from_pretrained(model_path, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16) # load with model checkpoint

    def reset(self, _logger=None):
        self.history = []

    def sync_history(self, history: List):
        self.history = history

class Planner(Agent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cur_subtask_idx = 0
        self.cur_subtask = None

    def inference_subtask(self, instruction: str, img_path: str=None) -> str:
        messages = [
            {"role": "system", "content": SYS_PLANNER},
            {"role": "user", "content": USR_SUBTASK_INTFRENCE.format(task_description=instruction, history=self.history if len(self.history) > 0 else "None")},
        ]
        if img_path:
            messages[1]["content"] = [
                {"type": "image_url", 'image_url': {"url": img_path}},
                {"type": "text", 'text': messages[1]["content"]}
            ]

        if not self.local:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages).choices[0].message.content
        else:
            response = qwen2generate(self.model, self.processor, messages)


        logging.info(f'''subtask inference {self.cur_subtask_idx}: {response}''')
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": USR_SUBTASK_INTFRENCE_FINAL})

        if not self.local:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages).choices[0].message.content
        else:
            response = qwen2generate(self.model, self.processor, messages)
        self.cur_subtask_idx += 1
        self.cur_subtask = response
        logging.info(f"current subtask: {self.cur_subtask}")
        return self.cur_subtask
    
    def add_subtask_history(self, feedback: str):
        self.history.append(f"""
Subtask {self.cur_subtask_idx}: {self.cur_subtask}
""")
        self.history.append(f"""
Feedback: {feedback}
""")


    def parse_actions(self, response: str, masks=None):
        pass


    def close(self):
        pass




class DetectionAgent(Agent):

    def detect(self, instruction: str, img_path: str=None) -> bool:
        messages = [
            {"role": "system", "content": SYS_PLANNER},
            {"role": "user", "content": USR_SUCCESS_DETECTION.format(task_description=instruction, history=self.history if len(self.history) > 0 else "None")},
        ]
        if img_path:
            messages[1]["content"] = [
                {"type": "image_url", 'image_url': {"url": img_path}},
                {"type": "text", 'text': messages[1]["content"]}
            ]

        if not self.local:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                max_tokens=1000).choices[0].message.content
        else:
            response = qwen2generate(self.model, self.processor, messages)
        logging.info(f"detection response: {response}")
        
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": USR_SUCCESS_DETECTION_FINAL})

        if not self.local:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                max_tokens=1000).choices[0].message.content
        else:
            response = qwen2generate(self.model, self.processor, messages)

        if "YES" in response:
            return True
        elif "NO" in response:
            return False
        else:
            raise ValueError(f"detection Invalid response: {response}")

    
    def detect_subtask(self, task_description: str, 
                            current_subtask_description: str, excution_response: str=None, img_path: str=None) -> str:
        messages = [
            {"role": "system", "content": SYS_PLANNER},
            {"role": "user", "content": USR_SUBTASK_SUCCESS_DETECTION.format(task_description=task_description, 
                                                                             excution_response=excution_response, 
                                                                             current_subtask_description=current_subtask_description)},
        ]
        if img_path:
            messages[1]["content"] = [
                {"type": "image_url", 'image_url': {"url": img_path}},
                {"type": "text", 'text': messages[1]["content"]}
            ]
        if not self.local:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                max_tokens=1000).choices[0].message.content
        else:
            response = qwen2generate(self.model, self.processor, messages)
        logging.info(f"detection response: {response}")
        
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": USR_SUCCESS_DETECTION_FINAL})

        if not self.local:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages).choices[0].message.content
        else:
            response = qwen2generate(self.model, self.processor, messages)

        if "YES" in response:
            return True
        elif "NO" in response:
            return False
        else:
            raise ValueError(f"detection Invalid response: {response}")
    
    

class UITars(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def output_action(self, current_subtask_description: str, img_path: str=None) -> str:
        if len(self.history) == 0:
            self.history.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", 'image_url': {"url": img_path}},
                        {"type": "text", 'text': SYS_CODE_UITARS_COMPUTER.format(language="English", instruction=current_subtask_description)}
                    ]
                }
            )
        else:
            self.history.append(
                {
                    "role": "user",
                    "content": [{"type": "image_url", 'image_url': {"url": img_path}}]
                }
            )
        if not self.local:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=self.history,
                max_tokens=1000).choices[0].message.content
        else:
            response = qwen2generate(self.model, self.processor, self.history)

        self.history.append({"role": "assistant", "content": response})
        logging.info(f'''output_action: {response}''')

        return response
    


