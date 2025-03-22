import json
import json5
from loguru import logger
import os
import sys
from typing import List, Dict, Any, Optional, Union, Tuple
from pydantic import BaseModel, Field, validator

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from agent_partially_connected.prompts import *
from agent_partially_connected.schema import *

from event import *
from action import *
from typing_process import *

# 键映射
KEY_MAPPING = {
    # 特殊键
    "Escape": "esc",
    "Oem_3": "`",  # 反引号键
    "Tab": "tab",
    "Capital": "capslock",
    "Lshift": "shift",
    "Rshift": "shift",
    "Lcontrol": "ctrl",
    "Rcontrol": "ctrl",
    "Lmenu": "alt",  # 左Alt
    "Rmenu": "alt",  # 右Alt
    "Lwin": "win",
    "Rwin": "win",
    "Space": "space",
    "Return": "enter",
    "Back": "backspace",
    "Delete": "delete",
    
    # 数字小键盘
    "Numlock": "num_lock",
    "Divide": "num_/",
    "Multiply": "num_*",
    "Subtract": "num_-",
    "Add": "num_+",
    "Decimal": "num_.",
    "Numpad0": "num_0",
    "Numpad1": "num_1",
    "Numpad2": "num_2",
    "Numpad3": "num_3",
    "Numpad4": "num_4",
    "Numpad5": "num_5",
    "Numpad6": "num_6",
    "Numpad7": "num_7",
    "Numpad8": "num_8",
    "Numpad9": "num_9",
    
    # 函数键
    "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4", "F5": "f5",
    "F6": "f6", "F7": "f7", "F8": "f8", "F9": "f9", "F10": "f10",
    "F11": "f11", "F12": "f12",
    
    # 方向键
    "Left": "left", "Right": "right", "Up": "up", "Down": "down",
    
    # OEM 键
    "Oem_1": ";", "Oem_Plus": "=", "Oem_Comma": ",", "Oem_Minus": "-",
    "Oem_Period": ".", "Oem_2": "/", "Oem_4": "[", "Oem_5": "\\",
    "Oem_6": "]", "Oem_7": "'",
    
    # 其他常用键
    "Home": "home", "End": "end", "PageUp": "pageup", "PageDown": "pagedown",
    "Insert": "insert", "Pause": "pause", "PrintScreen": "print_screen",
    "ScrollLock": "scroll_lock",
}

class KeyboardStateTracker(BaseModel):
    """跟踪键盘状态，识别快捷键组合"""
    active_modifiers: Dict[str, bool] = Field(default_factory=dict)
    active_keys: List[str] = Field(default_factory=list)
    last_key_combination: List[str] = Field(default_factory=list, description="记录完整的按键序列")
    modifier_keys: Set[str] = Field(
        default_factory=lambda: {
            "Lshift", "Rshift", "Lcontrol", "Rcontrol", 
            "Lmenu", "Rmenu", "Lwin", "Rwin"
        }
    )
    
    def press_key(self, key_name: str) -> None:
        """记录按下的键"""
        # 记录到完整序列
        self.last_key_combination.append(key_name)
        
        if key_name in self.modifier_keys:
            self.active_modifiers[key_name] = True
        else:
            # 确保非修饰键只添加一次
            if key_name not in self.active_keys:
                self.active_keys.append(key_name)
    
    def release_key(self, key_name: str) -> None:
        """记录释放的键"""
        if key_name in self.modifier_keys:
            self.active_modifiers.pop(key_name, None)
        elif key_name in self.active_keys:
            self.active_keys.remove(key_name)
    
    def get_hotkey_combination(self) -> Optional[str]:
        """获取快捷键组合"""
        # 如果没有记录任何按键，返回None
        if not self.last_key_combination:
            return None
            
        # 将修饰键映射为简短名称
        modifier_map = {
            "Lshift": "shift", "Rshift": "shift",
            "Lcontrol": "ctrl", "Rcontrol": "ctrl",
            "Lmenu": "alt", "Rmenu": "alt",
            "Lwin": "win", "Rwin": "win"
        }
        
        # 从完整的按键序列中提取非修饰键和修饰键
        modifiers = set()
        main_keys = []
        
        for key in self.last_key_combination:
            if key in self.modifier_keys:
                mapped_mod = modifier_map.get(key)
                if mapped_mod:
                    modifiers.add(mapped_mod)
            else:
                # 对于非修饰键，只保留最后一个不同的键
                mapped_key = KEY_MAPPING.get(key, key)
                if not main_keys or main_keys[-1] != mapped_key:
                    main_keys.append(mapped_key)
        
        # 如果没有主键，使用最后一个按键作为主键
        if not main_keys and self.last_key_combination:
            last_key = self.last_key_combination[-1]
            main_keys = [KEY_MAPPING.get(last_key, last_key)]
        
        # 按照约定顺序排列修饰键：ctrl, alt, shift, win
        ordered_modifiers = []
        for mod in ["ctrl", "alt", "shift", "win"]:
            if mod in modifiers:
                ordered_modifiers.append(mod)
        
        # 组合修饰键和主键
        if ordered_modifiers:
            return "+".join(ordered_modifiers + main_keys)
        elif main_keys:
            return main_keys[0]
        else:
            return None
    
    def reset(self) -> None:
        """重置状态"""
        self.active_modifiers.clear()
        self.active_keys.clear()
        self.last_key_combination.clear()


def deduplicate_scroll(script_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    去除连续的滚动事件，只保留最后一个滚动事件。
    
    Args:
        script_data: KeymouseGo脚本数据
    
    Returns:
        Dict[str, Any]: 处理后的脚本数据
    """
    new_script_data = script_data.copy()
    events = new_script_data.get("scripts", [])
    
    i = 0
    while i < len(events):
        event = events[i]
        
        if event.get('event_type') == "EM" and event.get('action_type')=="mouse wheel up":
            j = i + 1
            while j < len(events) and events[j].get('event_type') == "EM" and events[j].get('action_type')=="mouse wheel up":
                j += 1            
            # 保留最后一个滚动事件
            if j > i + 1:
                events = events[:i] + events[j-1:]

        elif event.get('event_type') == "EM" and event.get('action_type')=="mouse wheel down":
            j = i + 1
            while j < len(events) and events[j].get('event_type') == "EM" and events[j].get('action_type')=="mouse wheel down":
                j += 1            
            # 保留最后一个滚动事件
            if j > i + 1:
                events = events[:i] + events[j-1:]
        
        i += 1
    
    new_script_data["scripts"] = events
    return new_script_data


def remove_move(script_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    去除鼠标移动事件。
    
    Args:
        script_data: KeymouseGo脚本数据
    
    Returns:
        Dict[str, Any]: 处理后的脚本数据
    """
    new_script_data = script_data.copy()
    events = new_script_data.get("scripts", [])
    events = [event for event in events if not (event.get("event_type") == "EM" and event.get("action_type") == "mouse move")]
    new_script_data["scripts"] = events
    logger.debug(f'new_script_data: {new_script_data}')
    return new_script_data

def keymousego_to_action_space(script_data: Dict[str, Any], model_coord_width: int=1000, model_coord_height: int=1000) -> Tuple[List[str], List[str]]:
    """
    将脚本转换为 action space 代码。
    
    Args:
        script_data: KeymouseGo脚本数据
        model_coord_width: action space 的坐标范围 (默认 1000)
        model_coord_height: action space 的坐标范围 (默认 1000)
    
    Returns:
        Tuple[List[str], List[str]]: 转换后的操作字符串列表和对应的截图路径列表
    """
    script_model = ScriptData(scripts=[KMGEvent(**event) for event in script_data.get("scripts", [])])
    events = script_model.scripts
    
    actions_objects: List[Action] = []
    
    # 处理时间间隔和双击识别
    last_action = None
    keyboard_state = KeyboardStateTracker()
    double_click_count = 0
    
    # 跟踪快捷键序列的状态
    hotkey_start_index = -1
    
    i = 0
    while i < len(events):
        if double_click_count > 0:
            double_click_count -= 1
            i += 1
            continue
            
        event = events[i]
        
        # 处理长时间等待
        if event.delay >= 5000:
            actions_objects.append(Wait(screenshot=event.screenshot))
        
        # 处理鼠标事件
        if event.event_type == "EM":
            # 如果有待处理的快捷键，先提交
            if hotkey_start_index >= 0:
                hotkey = keyboard_state.get_hotkey_combination()
                if hotkey:
                    actions_objects.append(Hotkey(key=hotkey, screenshot=events[hotkey_start_index].screenshot))
                keyboard_state.reset()
                hotkey_start_index = -1
            
            # 解析坐标
            if isinstance(event.action, list) and len(event.action) >= 2:
                try:
                    x, y = [int(float(coord.strip("%")) * model_coord_width) for coord in event.action[:2]]
                    
                    # 识别双击
                    if (event.action_type == "mouse left down" and i + 3 < len(events) and
                        all(j < len(events) for j in range(i+1, i+4))):
                        
                        next1, next2, next3 = events[i+1], events[i+2], events[i+3]
                        
                        # 检查是否是双击模式：down→up→down→up 在相同位置
                        if (next1.event_type == "EM" and next2.event_type == "EM" and next3.event_type == "EM" and
                            next1.action_type == "mouse left up" and 
                            next2.action_type == "mouse left down" and 
                            next3.action_type == "mouse left up" and
                            next1.action == event.action and 
                            next2.action == event.action and 
                            next3.action == event.action and
                            (next1.delay + next2.delay + next3.delay) < 700):
                            
                            actions_objects.append(DoubleClick(x=x, y=y, screenshot=event.screenshot))
                            double_click_count = 3
                            i += 1
                            continue
                    
                    # 识别拖拽和单击
                    if event.action_type == "mouse left down":
                        last_action = ("left_down", (x, y))
                    
                    elif event.action_type == "mouse move":
                        last_action = ("move", (x, y))
                    
                    elif event.action_type == "mouse left up" and last_action:
                        if last_action[0] == "move":
                            x1, y1 = last_action[1]
                            actions_objects.append(Drag(x=x1, y=y1, end_x=x, end_y=y, screenshot=event.screenshot))
                        elif last_action[0] == "left_down":
                            actions_objects.append(Click(x=x, y=y, screenshot=event.screenshot))
                        last_action = None
                    
                    # 识别右键单击
                    elif event.action_type == "mouse right down":
                        last_action = ("right", (x, y))
                    
                    elif event.action_type == "mouse right up" and last_action and last_action[0] == "right":
                        actions_objects.append(RightClick(x=x, y=y, screenshot=event.screenshot))
                        last_action = None
                    
                    # 识别滚动
                    elif event.action_type in ["mouse wheel up", "mouse wheel down"]:
                        direction = "up" if event.action_type == "mouse wheel up" else "down"
                        actions_objects.append(Scroll(x=x, y=y, direction=direction, screenshot=event.screenshot))
                
                except (ValueError, TypeError) as e:
                    logger.error(f"❌ 无法解析鼠标坐标: {event.action} - {e}")
        
        # 处理键盘事件
        elif event.event_type == "EK":
            '''默认打字都预先处理为input事件了，这里不再处理'''
            if isinstance(event.action, list) and len(event.action) > 1:
                key_name = event.action[1]
                
                # 处理按键按下
                if event.action_type == "key down":
                    # 记录快捷键序列的开始
                    if hotkey_start_index < 0:
                        hotkey_start_index = i
                        keyboard_state.reset()  # 确保开始新序列时状态是干净的
                    
                    # 记录按下的键
                    keyboard_state.press_key(key_name)
                
                # 处理按键释放
                elif event.action_type == "key up":
                    # 记录释放的键
                    keyboard_state.release_key(key_name)
                    
                    # 当没有任何按键处于按下状态时，快捷键序列结束
                    if not keyboard_state.active_modifiers and not keyboard_state.active_keys:
                        hotkey = keyboard_state.get_hotkey_combination()
                        logger.debug(f"Hotkey combination detected: {hotkey}")
                        if hotkey:
                            actions_objects.append(Hotkey(key=hotkey, screenshot=events[hotkey_start_index].screenshot))
                        hotkey_start_index = -1
                        keyboard_state.reset()
        
        # 处理文本输入
        elif event.event_type == "EX" and event.action_type == "input":
            # 如果有待处理的快捷键，先提交
            if hotkey_start_index >= 0:
                keyboard_state.reset()
                hotkey_start_index = -1
                
            content = str(event.action)
            actions_objects.append(Type(content=content, screenshot=event.screenshot))
        
        i += 1
    
    # 处理最后可能未完成的快捷键序列
    if hotkey_start_index >= 0:
        hotkey = keyboard_state.get_hotkey_combination()
        if hotkey:
            actions_objects.append(Hotkey(key=hotkey, screenshot=events[hotkey_start_index].screenshot))
    
    # 生成操作字符串和截图列表
    action_strings = [str(action) for action in actions_objects]
    screenshots = [action.screenshot for action in actions_objects]
    
    return action_strings, screenshots



def script_to_sharegpt(script: Dict[str, Any], instruction: str) -> SharegptConversation:
    """
    将脚本转换为ShareGPT对话格式
    
    Args:
        script: KeymouseGo脚本数据
        instruction: 指令文本
    
    Returns:
        SharegptConversation: ShareGPT对话对象
    """
    actions, imgs = keymousego_to_action_space(script)
    logger.debug(f'len(actions): {len(actions)}, len(imgs): {len(imgs)}')
    messages = []
    
    for action, img in zip(actions, imgs):
        logger.debug(f'Action: {action}')
        logger.debug(f'Image: {img}')
        messages.append(SharegptMessage.user_message("<image>"))
        messages.append(SharegptMessage.assistant_message(action))
    # 添加系统指令到第一条消息
    if messages:
        messages[0].content = messages[0].content + SYS_CODE_UITARS_COMPUTER.format(
            language="Chinese", instruction=instruction)
    
    return SharegptConversation(messages=messages, images=imgs)

if __name__ == "__main__":
    # 测试脚本转换
    script_data = json5.load(open("actionSpace_KeymouseGo\\0317_2207\\script.json5"))
    script_data = remove_move(script_data)
    script_data = typing_process(script_data)
    script_data = deduplicate_scroll(script_data)
    for i, event in enumerate(script_data["scripts"]):
        logger.debug(f"Event {i+1}: {event}")
    conversation = script_to_sharegpt(script_data, "请在屏幕上点击左键")
    
    # 打印结果
    for conv in conversation.to_dict()['messages']:
        logger.info(conv['role'] + ": " + conv['content'])