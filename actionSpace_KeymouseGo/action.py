from typing import Optional

from pydantic import BaseModel, Field

# 定义Action类层次结构
class Action(BaseModel):
    """基础操作类"""
    name: str = Field(..., description="操作名称")
    screenshot: Optional[str] = Field(None, description="截图路径")

    def __str__(self) -> str:
        """返回操作的字符串表示"""
        return f"{self.name}()"

class MouseAction(Action):
    """鼠标操作基类"""
    x: int = Field(..., description="X坐标")
    y: int = Field(..., description="Y坐标")

class Click(MouseAction):
    """单击操作"""
    name: str = "click"

    def __str__(self) -> str:
        return f"click(start_box='<|box_start|>({self.x},{self.y})<|box_end|>')"

class DoubleClick(MouseAction):
    """双击操作"""
    name: str = "left_double"

    def __str__(self) -> str:
        return f"left_double(start_box='<|box_start|>({self.x},{self.y})<|box_end|>')"

class RightClick(MouseAction):
    """右键单击操作"""
    name: str = "right_single"

    def __str__(self) -> str:
        return f"right_single(start_box='<|box_start|>({self.x},{self.y})<|box_end|>')"

class Drag(MouseAction):
    """拖拽操作"""
    name: str = "drag"
    end_x: int = Field(..., description="结束X坐标")
    end_y: int = Field(..., description="结束Y坐标")

    def __str__(self) -> str:
        return (f"drag(start_box='<|box_start|>({self.x},{self.y})<|box_end|>', "
                f"end_box='<|box_start|>({self.end_x},{self.end_y})<|box_end|>')")

class Scroll(MouseAction):
    """滚动操作"""
    name: str = "scroll"
    direction: str = Field(..., description="滚动方向: 'up' 或 'down'")
    
    def __str__(self) -> str:
        return f"scroll(start_box='<|box_start|>({self.x},{self.y})<|box_end|>', direction='{self.direction}')"

class KeyboardAction(Action):
    """键盘操作基类"""
    pass

class Hotkey(KeyboardAction):
    """热键操作"""
    name: str = "hotkey"
    key: str = Field(..., description="键名")

    def __str__(self) -> str:
        return f"hotkey(key='{self.key}')"

class Type(KeyboardAction):
    """输入文本操作"""
    name: str = "type"
    content: str = Field(..., description="输入内容")

    def __str__(self) -> str:
        return f"type(content='{self.content}')"

class Wait(Action):
    """等待操作"""
    name: str = "wait"

    def __str__(self) -> str:
        return "wait()"