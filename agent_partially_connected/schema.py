from enum import Enum
from typing import Any, List, Literal, Optional, Union
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, field_validator, ValidationInfo
from PIL import Image


from agent_partially_connected.utils import *

class AgentState(str, Enum):
    """Agent execution states"""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class Function(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    """Represents a tool/function call in a message"""

    id: str
    type: str = "function"
    function: Function

class Content(BaseModel):
    """openai content. Can be text or image_url"""
    type: Literal["text", "image_url"]
    value: Union[str, Image.Image] = Field(None, description="Content value")
    
    @field_validator('value')
    def validate_image(cls, v, info: ValidationInfo):
        if isinstance(v, Image.Image) and not info.data['type'] == 'image_url':
            raise ValueError('Image content must be of type "image_url"')
        return v
    
    class Config:
        arbitrary_types_allowed = True

    
    def to_dict(self, decode:bool=True) -> dict:
        if self.type == "text":
            return {"type": self.type, self.type: self.value}
        if self.type == "image_url":
            if isinstance(self.value, Image.Image) or decode:
                return {"type": self.type, self.type: {"url": to_base64_openai_format(self.value)}}
            else:
                return {"type": self.type, self.type: {"url": self.value}}

                    
class LocalQwen2VLContent(Content):
    """qwen2vl content. Can be text or image"""
    type: Literal["text", "image"]
    value: str|Image.Image = Field(None, description="Content value")

    @field_validator('value')
    def validate_image(cls, v, info: ValidationInfo):
        if isinstance(v, Image.Image) and not info.data['type'] == 'image':
            raise ValueError('Image content must be of type "image"')
        return v
    
    class Config:
        arbitrary_types_allowed = True

    
    def to_dict(self, decode:bool=True) -> dict:
        if self.type == "text":
            return {"type": self.type, self.type: self.value}
        if self.type == "image":
            if isinstance(self.value, Image.Image) or decode:
                return {"type": self.type, self.type: to_base64_openai_format(self.value)}
            else:
                return {"type": self.type, self.type: self.value}

class Message(BaseModel):
    """
    Represents a chat message in the conversation
    In openai format, content can be list
    """

    role: Literal["system", "user", "assistant", "tool"] = Field(...)
    content: Optional[str|Content|List[Content]] = Field(default=None)
    tool_calls: Optional[List[ToolCall]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)

    def __add__(self, other) -> List["Message"]:
        """支持 Message + list 或 Message + Message 的操作"""
        if isinstance(other, list):
            return [self] + other
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> List["Message"]:
        """支持 list + Message 的操作"""
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """Convert message to dictionary format"""
        message = {"role": self.role}
        if self.content is not None:
            if isinstance(self.content, str):
                message["content"] = self.content
            elif isinstance(self.content, list):
                message["content"] = [content.to_dict() for content in self.content]
            else:
                message["content"] = self.content.to_dict()
        if self.tool_calls is not None:
            message["tool_calls"] = [tool_call.dict() for tool_call in self.tool_calls]
        if self.name is not None:
            message["name"] = self.name
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        return message

    @classmethod
    def user_message(cls, content: str|Content|List[Content]) -> "Message":
        """Create a user message"""
        return cls(role="user", content=content)

    @classmethod
    def system_message(cls, content: str|Content) -> "Message":
        """Create a system message"""
        return cls(role="system", content=content)

    @classmethod
    def assistant_message(cls, content: str|Content|List[Content] = None) -> "Message":
        """Create an assistant message"""
        return cls(role="assistant", content=content)

    @classmethod
    def tool_message(cls, content: str, name, tool_call_id: str) -> "Message":
        """Create a tool message"""
        return cls(role="tool", content=content, name=name, tool_call_id=tool_call_id)

    @classmethod
    def from_tool_calls(
        cls, tool_calls: List[Any], content: Union[str, List[str]] = "", **kwargs
    ):
        """Create ToolCallsMessage from raw tool calls.

        Args:
            tool_calls: Raw tool calls from LLM
            content: Optional message content
        """
        formatted_calls = [
            {"id": call.id, "function": call.function.model_dump(), "type": "function"}
            for call in tool_calls
        ]
        return cls(
            role="assistant", content=content, tool_calls=formatted_calls, **kwargs
        )
    
class SharegptMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(...)
    content: str

    @classmethod
    def user_message(cls, content: str) -> "SharegptMessage":
        """Create a user message"""
        return cls(role="user", content=content)

    @classmethod
    def system_message(cls, content: str) -> "SharegptMessage":
        """Create a system message"""
        return cls(role="system", content=content)

    @classmethod
    def assistant_message(cls, content: str = None) -> "SharegptMessage":
        """Create an assistant message"""
        return cls(role="assistant", content=content)

    # @classmethod
    # def tool_message(cls, content: str, name, tool_call_id: str) -> "SharegptMessage":
    #     """Create a tool message"""
    #     return cls(role="tool", content=content, name=name, tool_call_id=tool_call_id)

    # @classmethod
    # def from_tool_calls(
    #     cls, tool_calls: List[Any], content: Union[str, List[str]] = "", **kwargs
    # ):
    #     """Create ToolCallsMessage from raw tool calls.

    #     Args:
    #         tool_calls: Raw tool calls from LLM
    #         content: Optional message content
    #     """
    #     formatted_calls = [
    #         {"id": call.id, "function": call.function.model_dump(), "type": "function"}
    #         for call in tool_calls
    #     ]
    #     return cls(
    #         role="assistant", content=content, tool_calls=formatted_calls, **kwargs
    #     )

class SharegptConversation(BaseModel):
    messages: List[SharegptMessage] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)

    @field_validator('images')
    def validate_images_count(cls, v, info: ValidationInfo):
        if 'messages' not in info.data:
            return v
        
        image_tag_count = sum(message.content.count("<image>") for message in info.data['messages'])
        
        if len(v) != image_tag_count:
            raise ValueError(f"图片数量 ({len(v)}) 必须与消息中的 '<image>' 标记数量 ({image_tag_count}) 相匹配")
        
        return v

    def to_dict(self) -> dict:
        return {"messages": [{"role": msg.role, "content": msg.content} for msg in self.messages], "images": self.images}

class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)

    def add_message(self, message: Message) -> None:
        """Add a message to memory"""
        self.messages.append(message)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def add_messages(self, messages: List[Message]) -> None:
        """Add multiple messages to memory"""
        self.messages.extend(messages)

    def clear(self) -> None:
        """Clear all messages"""
        self.messages.clear()

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get n most recent messages"""
        return self.messages[-n:]

    def to_dict_list(self) -> List[dict]:
        """Convert messages to list of dicts"""
        return [msg.to_dict() for msg in self.messages]
    
    def len(self) -> int:
        return len(self.messages)
