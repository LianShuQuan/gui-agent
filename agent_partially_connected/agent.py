from typing import List
from abc import ABC, abstractmethod

from openai import OpenAI
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import torch
from pydantic import BaseModel
from pydantic.fields import Field
from logger import logger

from excutor import *
from prompts import *
from utils import *
from schema import *
from config.config import LLMSettings, config

class MLLM(BaseModel, ABC):
    name: str = Field(None, description="Model name")
    temperature: float = Field(1.0, description="Sampling temperature")
    max_tokens: int = Field(2048, description="Maximum tokens to generate")
    @abstractmethod
    def call(self) -> str:
        """Call the model"""

    @staticmethod
    def format_messages(messages: List[Union[dict, Message]]) -> List[dict]:
        """
        Format messages for LLM by converting them to OpenAI message format.

        Args:
            messages: List of messages that can be either dict or Message objects

        Returns:
            List[dict]: List of formatted messages in OpenAI format

        Raises:
            ValueError: If messages are invalid or missing required fields
            TypeError: If unsupported message types are provided

        Examples:
            >>> msgs = [
            ...     Message.system_message("You are a helpful assistant"),
            ...     {"role": "user", "content": "Hello"},
            ...     Message.user_message("How are you?")
            ... ]
            >>> formatted = LLM.format_messages(msgs)
        """
        formatted_messages = []

        for message in messages:
            if isinstance(message, dict):
                # If message is already a dict, ensure it has required fields
                if "role" not in message:
                    raise ValueError("Message dict must contain 'role' field")
                formatted_messages.append(message)
            elif isinstance(message, Message):
                # If message is a Message object, convert it to dict
                formatted_messages.append(message.to_dict())
            else:
                raise TypeError(f"Unsupported message type: {type(message)}")

        # Validate all messages have required fields
        for msg in formatted_messages:
            if msg["role"] not in ["system", "user", "assistant", "tool"]:
                raise ValueError(f"Invalid role: {msg['role']}")
            if "content" not in msg and "tool_calls" not in msg:
                raise ValueError(
                    "Message must contain either 'content' or 'tool_calls'"
                )

        return formatted_messages

class LocalMLLM(MLLM):
    processor_path: str = Field(..., description="Qwen2VL Processor path")
    path: str = Field(..., description="model path")

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.processor = AutoProcessor.from_pretrained(self.processor_path)
    #     self.model = Qwen2VLForConditionalGeneration.from_pretrained(self.model_path, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)

    def model_post_init(self, __context):
        # 这个方法会在模型初始化后自动调用
        self._processor = AutoProcessor.from_pretrained(self.processor_path)
        self._model = Qwen2VLForConditionalGeneration.from_pretrained(self.path, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)

    def call(self, messages: List[Message]) -> str:
        return qwen2generate(self._model, self._processor, MLLM.format_messages(messages))
    

class ApiMLLM(MLLM):
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key")

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def model_post_init(self, __context):
        # 这个方法会在模型初始化后自动调用
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def call(self, messages: List[Message], temperature: Optional[float]=None, max_retry=5) -> str:
        if temperature is None:
            temperature = self.temperature
        logger.debug(f"messages: {[message.to_dict_not_show_img() for message in messages]}")
        try_times = 0
        while True:
            if try_times >= max_retry:
                logger.error(f"Reach max retry times to fetch response from client, as error flag.")
                return f"Reach max retry times to fetch response from client, as error flag."
            try:
                
                response = self._client.chat.completions.create(model=self.name, messages=MLLM.format_messages(messages), temperature=temperature, max_tokens=self.max_tokens)
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Error when fetching response from client, with response: {response}")
                try_times += 1

class BaseAgent():
    agent_name: str = None
    memory: Memory
    mllm: MLLM
    subtasks: list = []

    def __init__(self, config_name: str = "default", llm_config: Optional[LLMSettings] = None):
        """
        config_name is llm.config_name in toml file
        """
        llm_config = llm_config or config.llm.get(config_name)
        self.agent_name = llm_config.agent_name
        if llm_config.local:
            self.mllm = LocalMLLM(name=llm_config.model, processor_path=llm_config.processor_path,
                                  path=llm_config.model_path, temperature=llm_config.temperature, max_tokens=llm_config.max_tokens)
        else:
            self.mllm = ApiMLLM(name=llm_config.model, base_url=llm_config.base_url, api_key=llm_config.api_key, temperature=llm_config.temperature, max_tokens=llm_config.max_tokens)
        self.memory = Memory()

    def reset(self):
        self.memory = Memory()
        self.cur_subtask = []

    def cur_subtask(self):
        return self.subtasks[-1]
    
    def cur_subtask_idx(self):
        return len(self.subtasks) - 1

class Planner(BaseAgent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def inference_subtask(self, instruction: str, img: str|Image.Image=None) -> str:
        messages = []
        messages.append(Message.system_message(SYS_PLANNER))
        if img:
            messages.append(Message.user_message([Content(type="image_url", value=img), Content(type="text", value=USR_SUBTASK_INTFRENCE.format(task_description=instruction, subtasks=self.subtasks if len(self.subtasks) > 0 else "None"))]))
        else:
            messages.append(Message.user_message(USR_SUBTASK_INTFRENCE.format(task_description=instruction, subtasks=self.subtasks if len(self.subtasks) > 0 else "None")))
        response = self.mllm.call(messages)
        logger.info(f'''subtask inference: {response}''')

        self.subtasks.append(response)

        logger.info(f"subtask {self.cur_subtask_idx()}: {self.cur_subtask()}")
        return self.cur_subtask()
    
    def detect(self, instruction: str, img: str|Image.Image=None) -> bool:

        messages = [Message.system_message(SYS_PLANNER)]
        if img:
            messages.append(Message.user_message([Content(type="text",value=USR_SUCCESS_DETECTION.format(task_description=instruction, history=self.subtasks if len(self.subtasks) > 0 else "None")),
                                                  Content(type="image_url", value=img)]))
        else:
            messages.append(Message.user_message(USR_SUCCESS_DETECTION.format(task_description=instruction, history=self.subtasks if len(self.subtasks) > 0 else "None")))
        response = self.mllm.call(messages)
        logger.info(f"detection response: {response}")
        messages.append(Message.assistant_message(response))

        messages.append(Message.user_message(USR_SUCCESS_DETECTION_FINAL))
        response = self.mllm.call(messages)
        self.memory.add_messages(messages)
        if "YES" in response:
            return True
        elif "NO" in response:
            return False
        else:
            raise ValueError(f"detection response Invalid: {response}")
    

    
    

class UITars(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def output_action(self, current_subtask_description: str, img: str|Image.Image=None) -> str:
        if self.memory.len() == 0:
            self.memory.add_message(Message.user_message([Content(type="text", value=SYS_CODE_UITARS_COMPUTER.format(language="Chinese", instruction=current_subtask_description)),
                                                      Content(type="image_url", value=img)]))
        else:
            self.memory.add_message(Message.user_message([Content(type="image_url", value=img)]))
        response = self.mllm.call(self.memory.messages)
        logger.info(f'''output_action: {response}''')
        self.memory.add_message(Message.assistant_message(response))
        return response
    


