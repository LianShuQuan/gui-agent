import json5
from loguru import logger
from pydantic import BaseModel, Field
from typing import List, Optional, Set, Union, Tuple, Dict, Any

# 定义基础数据模型
class KMGEvent(BaseModel):
    type: str = "event"
    delay: int
    event_type: str
    action_type: str
    action: Union[List[Any], str] = Field(..., description="参数列表")
    screenshot: Optional[str] = None

class ScriptData(BaseModel):
    scripts: List[KMGEvent]