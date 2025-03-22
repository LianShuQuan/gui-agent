import json5
from loguru import logger
from pydantic import BaseModel, Field
from typing import List, Optional, Set, Union, Tuple, Dict, Any
from event import *

# 辅助类模型
class KeyboardState(BaseModel):
    active_modifiers: Set[str] = Field(default_factory=set)
    modifier_keys: Set[str] = Field(
        default_factory=lambda: {
            "Lshift", "Rshift", "Lcontrol", "Rcontrol", 
            "Lmenu", "Rmenu", "Lwin", "Rwin"
        }
    )
    
    def add_modifier(self, key_name: str) -> None:
        if key_name in self.modifier_keys:
            self.active_modifiers.add(key_name)
    
    def remove_modifier(self, key_name: str) -> None:
        if key_name in self.active_modifiers:
            self.active_modifiers.remove(key_name)
    
    def has_modifiers(self) -> bool:
        return len(self.active_modifiers) > 0

class ShortcutState(BaseModel):
    events: List[KMGEvent] = Field(default_factory=list)
    keys: Set[str] = Field(default_factory=set)
    tracking: bool = False
    
    def start(self, event: KMGEvent) -> None:
        self.reset()
        self.tracking = True
        self.add_key(event)
    
    def add_key(self, event: KMGEvent) -> None:
        self.events.append(event)
        if isinstance(event.action, list) and len(event.action) > 1:
            self.keys.add(event.action[1])
    
    def reset(self) -> None:
        self.events = []
        self.keys = set()
        self.tracking = False
    
    def is_tracking(self) -> bool:
        return self.tracking
    
    def get_events(self) -> List[KMGEvent]:
        return self.events

class TypingState(BaseModel):
    buffer: str = ""
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    last_key_time: int = 0
    timeout: int = 4000
    
    def should_start_new_sequence(self, current_time: int) -> bool:
        return (not self.buffer or 
                (self.last_key_time > 0 and 
                 current_time - self.last_key_time > self.timeout))
    
    def update_time(self, current_time: int) -> None:
        self.last_key_time = current_time
    
    def is_empty(self) -> bool:
        return self.buffer == ""

# 辅助函数
def is_keyboard_event(event: KMGEvent) -> bool:
    return (event.event_type == "EK" and 
            event.action_type in ["key down", "key up"])

def is_modifier_key(key_name: str) -> bool:
    modifier_keys = {
        "Lshift", "Rshift", "Lcontrol", "Rcontrol", 
        "Lmenu", "Rmenu", "Lwin", "Rwin"
    }
    return key_name in modifier_keys

def is_special_key(key_name: str) -> bool:
    special_keys = {
        "Escape", "Tab", "Capital", "Return", "Back", "Delete", "Home", "End", 
        "PageUp", "PageDown", "Insert", "Pause", "PrintScreen", "ScrollLock", "Numlock",
        "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
        "Left", "Right", "Up", "Down", "Divide", "Multiply", "Subtract", "Add", "Decimal"
    }
    return key_name in special_keys

def get_character_representation(key_name: str) -> str:
    # 字母和数字
    if len(key_name) == 1 and (key_name.isalpha() or key_name.isdigit()):
        return key_name.lower()
    
    # 空格
    if key_name == "Space":
        return " "
    
    # OEM键映射
    oem_keys = {
        "Oem_1": ";", "Oem_Plus": "=", "Oem_Comma": ",", "Oem_Minus": "-",
        "Oem_Period": ".", "Oem_2": "/", "Oem_3": "`", "Oem_4": "[",
        "Oem_5": "\\", "Oem_6": "]", "Oem_7": "'"
    }
    if key_name in oem_keys:
        return oem_keys[key_name]
    
    # 数字小键盘
    numpad_keys = {
        "Numpad0": "0", "Numpad1": "1", "Numpad2": "2", "Numpad3": "3", "Numpad4": "4",
        "Numpad5": "5", "Numpad6": "6", "Numpad7": "7", "Numpad8": "8", "Numpad9": "9"
    }
    if key_name in numpad_keys:
        return numpad_keys[key_name]
    
    # 默认返回键名
    return key_name

def calculate_current_time(events: List[KMGEvent], index: int) -> int:
    return sum(e.delay for e in events[:index+1])

def flush_typing_buffer(typing_state: TypingState, processed_events: List[KMGEvent], 
                        events: List[KMGEvent] = None, end_index: int = None) -> None:
    typing_state.end_index = end_index
    logger.debug(f"Flushing typing buffer: {typing_state.buffer}")
    
    if not typing_state.is_empty():
        screenshot = None
        if events and typing_state.end_index is not None and typing_state.end_index < len(events):
            screenshot = events[typing_state.end_index].screenshot
            
        delay = 0
        if typing_state.start_index is not None and events:
            delay = events[typing_state.start_index].delay
            
        input_event = KMGEvent(
            type="event",
            event_type="EX",
            delay=delay,
            action_type="input",
            action=typing_state.buffer,
            screenshot=screenshot
        )
        
        processed_events.append(input_event)
        logger.debug(f"Added typing event: {processed_events[-1]}")
        typing_state.buffer = ""
        typing_state.start_index = None

def append_shortcut_events(shortcut_state: ShortcutState, processed_events: List[KMGEvent]) -> None:
    if shortcut_state.is_tracking():
        events = shortcut_state.get_events()
        if events:
            for event in events:
                processed_events.append(event)

def process_typing_key(event: KMGEvent, events: List[KMGEvent], 
                       processed_events: List[KMGEvent], index: int,
                       typing_state: TypingState) -> None:
    
    if not isinstance(event.action, list) or len(event.action) < 2:
        return
    
    key_name = event.action[1]
    
    # 获取字符表示
    char = get_character_representation(key_name)
    
    # 计算当前时间
    current_time = calculate_current_time(events, index)
    
    # 检查是否需要创建新的打字缓冲区（首次或超时）
    if typing_state.should_start_new_sequence(current_time):
        flush_typing_buffer(typing_state, processed_events, events, index)
        
        # 创建新的打字缓冲区
        typing_state.buffer = char
        typing_state.start_index = index
    else:
        # 添加到现有缓冲区
        typing_state.buffer += char
    
    # 更新时间
    typing_state.update_time(current_time)

# 主处理函数
def typing_process(script_data: Dict[str, Any]) -> Dict[str, List[KMGEvent]]:
    """
    处理脚本数据，将连续的键盘输入识别为打字操作，将修饰键组合识别为快捷键。
    
    Args:
        script_data: 包含脚本事件的字典，格式为 {"scripts": [事件列表]}
        
    Returns:
        处理后的脚本数据，相同格式
    """
    # 将输入数据转换为Pydantic模型
    script_model = ScriptData(scripts=[KMGEvent(**event) for event in script_data.get("scripts", [])])
    events = script_model.scripts
    processed_events = []
    
    # 初始化各种状态跟踪
    keyboard_state = KeyboardState()
    typing_state = TypingState()
    shortcut_state = ShortcutState()
    
    # 跟踪哪些按键被用作打字，这些按键的key up事件将被忽略
    typing_keys = set()
    
    i = 0
    while i < len(events):
        event = events[i]
        
        # 1. 非键盘事件直接处理
        if not is_keyboard_event(event):
            # 先处理未完成的打字缓冲区
            flush_typing_buffer(typing_state, processed_events, events, i-1)
            # 结束任何正在进行的快捷键序列
            shortcut_state.reset()
            processed_events.append(event)
            i += 1
            continue
        
        # 2. 处理键盘事件 - 确保action是list类型
        if not isinstance(event.action, list) or len(event.action) < 3:
            logger.error(f"Invalid keyboard event: {event}")
            
        key_code, key_name, _ = event.action[:3]
        action_type = event.action_type
        
        # 3. 处理按键按下事件
        if action_type == "key down":
            # 更新修饰键状态
            if is_modifier_key(key_name):
                keyboard_state.add_modifier(key_name)
                # 如果正在记录快捷键，添加这个修饰键
                if shortcut_state.is_tracking():
                    shortcut_state.add_key(event)
                else:
                    # 开始新的快捷键序列
                    shortcut_state.start(event)
                
                # 如果有未完成的打字，先提交
                flush_typing_buffer(typing_state, processed_events, events, i-1)
                
                # 不立即添加到processed_events，等待完整快捷键
                i += 1
                continue
            
            # 快捷键处理（有修饰键激活时的按键）
            if keyboard_state.has_modifiers():
                flush_typing_buffer(typing_state, processed_events, events, i-1)
                
                # 添加到快捷键序列
                shortcut_state.add_key(event)
                
                # 不立即添加到processed_events，等待完整快捷键
                i += 1
                continue
            
            # 特殊键处理
            if is_special_key(key_name):
                flush_typing_buffer(typing_state, processed_events, events, i-1)
                # 结束任何正在进行的快捷键序列
                if shortcut_state.is_tracking():
                    append_shortcut_events(shortcut_state, processed_events)
                    shortcut_state.reset()
                
                processed_events.append(event)
                i += 1
                continue
            
            # 可打字字符处理
            # 首先结束任何正在进行的快捷键序列
            if shortcut_state.is_tracking():
                append_shortcut_events(shortcut_state, processed_events)
                shortcut_state.reset()
            
            # 标记这个按键为打字用途，其key up事件将被忽略
            typing_keys.add(key_code)
            
            process_typing_key(event, events, processed_events, i, typing_state)
            i += 1
            continue
            
        # 4. 处理按键抬起事件
        elif action_type == "key up":
            # 检查这个key up是否是打字键的对应事件
            if key_code in typing_keys:
                # 忽略打字键的key up事件
                typing_keys.remove(key_code)
                i += 1
                continue
            
            # 更新修饰键状态
            if is_modifier_key(key_name):
                keyboard_state.remove_modifier(key_name)
                
                # 如果是快捷键的一部分，添加到快捷键序列
                if shortcut_state.is_tracking():
                    shortcut_state.add_key(event)
                    
                    # 如果所有修饰键都已抬起，结束快捷键序列
                    if not keyboard_state.has_modifiers():
                        append_shortcut_events(shortcut_state, processed_events)
                        shortcut_state.reset()
                    
                    i += 1
                    continue
            else:
                # 非修饰键抬起，可能是快捷键操作的一部分
                if shortcut_state.is_tracking():
                    shortcut_state.add_key(event)
                    
                    # 不立即完成快捷键序列，等待所有修饰键抬起
                    i += 1
                    continue
            
            # 其他情况的key up事件
            processed_events.append(event)
            i += 1
            continue
    
    # 5. 处理结束时的缓冲区
    flush_typing_buffer(typing_state, processed_events, events, i-1 if i > 0 else 0)
    
    # 6. 处理未完成的快捷键序列
    if shortcut_state.is_tracking():
        append_shortcut_events(shortcut_state, processed_events)
    
    # 将处理结果转换回字典格式
    return {"scripts": [event.dict() for event in processed_events]}


if __name__=='__main__':
    script_data = json5.load(open("actionSpace_KeymouseGo\\0316_2254\\script.json5"))
    print("Original script:")
    for event in script_data["scripts"]:
        print(event)
    processed_data = typing_process(script_data)
    print("\nProcessed script:")
    for event in processed_data["scripts"]:
        print(event)