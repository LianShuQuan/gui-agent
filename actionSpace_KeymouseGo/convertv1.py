import json
import pyautogui
from loguru import logger
import os
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
parent_dir = os.path.dirname(parent_dir)
sys.path.append(parent_dir)
from agent_partially_connected.prompts import *
from agent_partially_connected.schema import *

# action space 的坐标范围是默认0-1000，keymousego的坐标范围是0-1

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
    "F1": "f1",
    "F2": "f2",
    "F3": "f3",
    "F4": "f4",
    "F5": "f5",
    "F6": "f6",
    "F7": "f7",
    "F8": "f8",
    "F9": "f9",
    "F10": "f10",
    "F11": "f11",
    "F12": "f12",
    
    # 方向键
    "Left": "left",
    "Right": "right",
    "Up": "up",
    "Down": "down",
    
    # OEM 键
    "Oem_1": ";",  # 分号键
    "Oem_Plus": "=",  # 等号键
    "Oem_Comma": ",",  # 逗号键
    "Oem_Minus": "-",  # 减号键
    "Oem_Period": ".",  # 句点键
    "Oem_2": "/",  # 斜杠键
    "Oem_4": "[",  # 左方括号键
    "Oem_5": "\\",  # 反斜杠键
    "Oem_6": "]",  # 右方括号键
    "Oem_7": "'",  # 单引号键
    
    # 其他常用键
    "Home": "home",
    "End": "end",
    "PageUp": "pageup",
    "PageDown": "pagedown",
    "Insert": "insert",
    "Pause": "pause",
    "PrintScreen": "print_screen",
    "ScrollLock": "scroll_lock",
    
    # 字母键和数字键保持不变
    "A": "a",
    "B": "b",
    "C": "c",
    # ... 其余字母键类似
    "0": "0",
    "1": "1",
    "2": "2",
    # ... 其余数字键类似
}






def _action_coord2keymousego_str(x, y, model_coord_width=1000, model_coord_height=1000):
    
    rel_x = x / model_coord_width
    rel_y = y / model_coord_height
    return f"{rel_x:.5f}%", f"{rel_y:.5f}%"

def _action_space_to_keymousego(actions):
    """将 action space 指令转换为 JSON 脚本格式"""
    json_script = []
    last_time = 0  # 记录上一个动作的时间
    
    for action in actions:
        if action.startswith("click") or action.startswith("left_double") or action.startswith("right_single"):
            action_type = "mouse left down" if "click" in action else "mouse right down" if "right_single" in action else "mouse left down"
            start_box = action.split("start_box='<|box_start|>(")[1].split(")<|box_end|>'")[0]
            x, y = map(int, start_box.split(","))
            rel_x, rel_y = _action_coord2keymousego_str(x, y)

            if "left_double" in action:  # 处理双击
                json_script.append([last_time, "EM", "mouse left down", [rel_x, rel_y]])
                json_script.append([50, "EM", "mouse left up", [rel_x, rel_y]])
                json_script.append([50, "EM", "mouse left down", [rel_x, rel_y]])
                json_script.append([50, "EM", "mouse left up", [rel_x, rel_y]])
            else:  # 单击或右键单击
                json_script.append([last_time, "EM", action_type, [rel_x, rel_y]])
                json_script.append([50, "EM", action_type.replace("down", "up"), [rel_x, rel_y]])  # 50ms 后抬起
        elif action.startswith("drag"):
            start_box = action.split("start_box='<|box_start|>(")[1].split(")<|box_end|>'")[0]
            end_box = action.split("end_box='<|box_start|>(")[1].split(")<|box_end|>'")[0]
            x1, y1 = map(int, start_box.split(","))
            x2, y2 = map(int, end_box.split(","))
            rel_x1, rel_y1 = _action_coord2keymousego_str(x1, y1)
            rel_x2, rel_y2 = _action_coord2keymousego_str(x2, y2)

            json_script.append([last_time, "EM", "mouse left down", [rel_x1, rel_y1]])
            json_script.append([100, "EM", "mouse move", [rel_x2, rel_y2]])
            json_script.append([100, "EM", "mouse left up", [rel_x2, rel_y2]])

        elif action.startswith("hotkey"):
            key = action.split("key='")[1].split("'")[0]
            json_script.append([last_time, "EK", "key down", [70, key, 0]])
            json_script.append([50, "EK", "key up", [70, key, 0]])

        elif action.startswith("type"):
            content = action.split("content='")[1].split("'")[0]
            json_script.append([last_time, "EX", "input", content])

        elif action.startswith("scroll"):
            start_box = action.split("start_box='<|box_start|>(")[1].split(")<|box_end|>'")[0]
            direction = action.split("direction='")[1].split("'")[0]
            x, y = map(int, start_box.split(","))
            rel_x, rel_y = _action_coord2keymousego_str(x, y)
            action_type = "mouse wheel up" if direction == "up" else "mouse wheel down"
            json_script.append([last_time, "EM", action_type, [rel_x, rel_y]])

        elif action.startswith("wait"):
            json_script.append([5000, "EX", "wait", ""])

        last_time = 100  # 每个动作默认间隔 100ms

    return json.dumps(json_script, indent=4, ensure_ascii=False)




def keymousego_to_action_space(script, model_coord_width=1000, model_coord_height=1000):
    """
    将脚本转换为 action space 代码。
    
    :param script: 操作序列
    :param model_coord_width: action space 的坐标范围 (默认 1000)
    :param model_coord_height: action space 的坐标范围 (默认 1000)
    :return: 转换后的 action space 代码
    """
    imgs= []
    actions = []
    
    # 处理时间间隔
    last_action = None
    double_click_count = 0

    for i in range(len(script)):
        if double_click_count > 0:
            double_click_count -= 1
            continue

        entry = script[i]
        if len(entry) == 4:
            wait_time, action_type, action, params = entry
        if len(entry) == 5:
            wait_time, action_type, action, params, img_path = entry

        if wait_time >= 5000:  # 如果超过5s，插入 wait()
            actions.append("wait()")
            if len(imgs) == 0:
                imgs.append("")
                logger.error(f"❌ 未找到截图：{entry}")
            imgs.append(imgs[-1])

        if action_type == "EM":  # 处理鼠标操作
            x, y = [int(float(coord.strip("%")) * model_coord_width) for coord in params]

            # 识别鼠标左键双击
            if action == "mouse left down" and i + 3 < len(script):
                next1 = script[i + 1]
                next2 = script[i + 2]
                next3 = script[i + 3]
                if (next1[0] + next2[0] + next3[0]) > 700:
                    logger.debug(f"❌ 间隔过长，判定为非双击：{entry}, {next1}, {next2}, {next3}")
                if next1[3]!=params or next2[3]!=params or next3[3]!=params:
                    logger.debug(f"❌ 双击坐标不一致，判定为非双击：{entry}, {next1}, {next2}, {next3}")
                # 确保模式是：down → up → down → up（间隔短时间）
                if (next1[2] == "mouse left up" and next2[2] == "mouse left down" and next3[2] == "mouse left up")\
                    and (next1[0] + next2[0] + next3[0]) < 700\
                    and next1[3] == params and next2[3] == params and next3[3] == params:
                    actions.append(f"left_double(start_box='<|box_start|>({x},{y})<|box_end|>')")
                    imgs.append(img_path)
                    double_click_count = 3  # 标记已识别双击

            # 识别拖拽和左键单击操作
            if action == "mouse left down":
                last_action = ("left_down", (x, y))

            elif action == "mouse move":
                last_action = ("move", (x, y))

            elif action == "mouse left up" and last_action:
                if last_action[0] == "move":
                    x1, y1 = last_action[1]
                    actions.append(f"drag(start_box='<|box_start|>({x1},{y1})<|box_end|>', "
                                   f"end_box='<|box_start|>({x},{y})<|box_end|>')")
                    imgs.append(img_path)
                elif last_action[0] == "left_down":
                    actions.append(f"click(start_box='<|box_start|>({x},{y})<|box_end|>')")
                    imgs.append(img_path)
                last_action = None  # 重置

            # 识别鼠标右键单击
            elif action == "mouse right down":
                last_action = ("right", (x, y))

            elif action == "mouse right up" and last_action and last_action[0] == "right":
                actions.append(f"right_single(start_box='<|box_start|>({x},{y})<|box_end|>')")
                imgs.append(img_path)
                last_action = None  # 重置



        elif action_type == "EK":  # 处理键盘操作
            if action == "key down":
                last_key = params[1]
            elif action == "key up" and last_key == params[1]:
                actions.append(f"hotkey(key='{last_key}')")
                imgs.append(img_path)
                last_key = None  # 重置

        elif action_type == "EX":  # 处理输入文本
            if action == "input":
                actions.append(f"type(content='{params}\\n')")
                imgs.append(img_path)

    return actions, imgs


def script_to_sharegpt(script, instruction) -> SharegptConversation:
    actions, imgs = keymousego_to_action_space(script)
    messages = []
    for action, img in zip(actions, imgs):
        messages.append(SharegptMessage.user_message("<image>"))
        messages.append(SharegptMessage.assistant_message(action))
    messages[0].content = messages[0].content + SYS_CODE_UITARS_COMPUTER.format(language="Chinese", instruction=instruction)
    return SharegptConversation(messages=messages, images=imgs)






def process_keyboard_events(script_data):
    events = script_data.get("scripts", [])
    processed_events = []
    
    # 打字缓冲区
    typing_buffer = ""
    typing_start_index = None
    typing_total_delay = 0
    last_key_time = 0
    typing_timeout = 1000  # 1秒无输入视为新打字操作
    
    # 活跃的修饰键
    active_modifiers = 0
    
    i = 0
    while i < len(events):
        event = events[i]
        
        # 非键盘事件或非按键事件，直接添加并继续
        if event["event_type"] != "EK" or event["action_type"] not in ["key down", "key up"]:
            # 先处理未完成的打字缓冲区
            if typing_buffer:
                # 创建input事件
                input_event = {
                    "type": "event",
                    "event_type": "EX",
                    "delay": events[typing_start_index]["delay"],
                    "action_type": "input",
                    "action": typing_buffer
                }
                
                # 替换起始事件，移除中间的键盘事件
                processed_events.append(input_event)
                typing_buffer = ""
                typing_start_index = None
            
            processed_events.append(event)
            i += 1
            continue
        
        # 处理键盘事件
        key_code, key_name, modifiers = event["action"]
        
        # 修饰键状态更新
        if key_name in ["SHIFT", "CONTROL", "ALT", "WIN"]:
            if event["action_type"] == "key down":
                active_modifiers |= get_modifier_flag(key_name)
            elif event["action_type"] == "key up":
                active_modifiers &= ~get_modifier_flag(key_name)
            
            processed_events.append(event)
            i += 1
            continue
        
        # 处理快捷键（有修饰键按下的情况）
        if active_modifiers > 0 and event["action_type"] == "key down":
            # 处理未完成的打字缓冲区
            if typing_buffer:
                input_event = {
                    "type": "event",
                    "event_type": "EX",
                    "delay": events[typing_start_index]["delay"],
                    "action_type": "input",
                    "action": typing_buffer
                }
                processed_events.append(input_event)
                typing_buffer = ""
                typing_start_index = None
            
            # 原样保留快捷键事件
            processed_events.append(event)
            i += 1
            continue
        
        # 处理特殊键（非打字字符）
        is_typing_char = is_typable_character(key_code, key_name)
        if not is_typing_char and event["action_type"] == "key down":
            # 处理未完成的打字缓冲区
            if typing_buffer:
                input_event = {
                    "type": "event",
                    "event_type": "EX",
                    "delay": events[typing_start_index]["delay"],
                    "action_type": "input",
                    "action": typing_buffer
                }
                processed_events.append(input_event)
                typing_buffer = ""
                typing_start_index = None
            
            # 原样保留特殊键事件
            processed_events.append(event)
            i += 1
            continue
        
        # 处理正常打字字符的key down事件
        if is_typing_char and event["action_type"] == "key down":
            current_time = sum(e["delay"] for e in events[:i])
            
            # 检查是否需要创建新的打字缓冲区（首次或超时）
            if typing_buffer == "" or (current_time - last_key_time) > typing_timeout:
                # 如果有旧的未处理缓冲区，先处理
                if typing_buffer:
                    input_event = {
                        "type": "event",
                        "event_type": "EX",
                        "delay": events[typing_start_index]["delay"],
                        "action_type": "input",
                        "action": typing_buffer
                    }
                    processed_events.append(input_event)
                
                # 创建新的打字缓冲区
                typing_buffer = key_name.lower() if key_name.isalpha() and len(key_name) == 1 else key_name
                typing_start_index = i
            else:
                # 添加到现有缓冲区
                typing_buffer += key_name.lower() if key_name.isalpha() and len(key_name) == 1 else key_name
            
            last_key_time = current_time
            
            # 跳过这个key down和对应的key up（如果存在）
            next_index = i + 1
            if (next_index < len(events) and 
                events[next_index]["event_type"] == "EK" and 
                events[next_index]["action_type"] == "key up" and
                events[next_index]["action"][0] == key_code):
                i += 2
            else:
                i += 1
            continue
        
        # 其他情况，原样保留事件
        processed_events.append(event)
        i += 1
    
    # 处理结束时的缓冲区
    if typing_buffer:
        input_event = {
            "type": "event",
            "event_type": "EX",
            "delay": events[typing_start_index]["delay"] if typing_start_index is not None else 0,
            "action_type": "input",
            "action": typing_buffer
        }
        processed_events.append(input_event)
    
    return {"scripts": processed_events}

def get_modifier_flag(key_name):
    """返回修饰键对应的标志位"""
    if key_name == "SHIFT":
        return 1
    elif key_name == "CONTROL":
        return 2
    elif key_name == "ALT":
        return 4
    elif key_name == "WIN":
        return 8
    return 0

def is_typable_character(key_code, key_name):
    """判断一个键是否为可打字字符"""
    # 可以根据需要调整此函数
    # ASCII可打印字符范围: 32-126
    if 32 <= key_code <= 126:
        return True
    # 空格、回车等某些特殊键也可以算作打字
    if key_name in [" ", "SPACE"]:
        return True
    return False





if __name__ == "__main__":

# 要遍历的目录
    folders = ["excel", "word", "ppt"]

    # 遍历每个顶级文件夹
    for folder in folders:
        # 为每个顶级文件夹初始化数据列表
        data = []
        
        # 遍历顶级文件夹中的所有子文件夹
        for root, dirs, files in os.walk(folder):
            # 检查当前文件夹中是否有 script.txt
            if "script.txt" in files:
                script_path = os.path.join(root, "script.txt")
                print(f"处理文件: {script_path}")
                
                try:
                    # 读取 script.txt 文件
                    with open(script_path, "r", encoding="utf-8") as script_file:
                        json_script = json.load(script_file)
                    instruction = json_script[0]
                    json_script = json_script[1:]
                    # 转换脚本
                    conv = script_to_sharegpt(json_script, "请在屏幕上点击左键")
                    
                    # 添加到当前文件夹的数据列表
                    data.append(conv.to_dict())
                    
                except Exception as e:
                    print(f"处理文件 {script_path} 时出错: {str(e)}")
        
        # 为当前文件夹写入结果到对应的 JSON 文件
        output_file = f"gui_agent_{folder}_action.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"处理完成 {folder} 文件夹，共处理了 {len(data)} 个文件，保存到 {output_file}")

    print("所有文件夹处理完成")



    




    # # 示例 Action Space
    # actions = [
    #     "click(start_box='<|box_start|>(101,204)<|box_end|>')",
    #     "left_double(start_box='<|box_start|>(520,500)<|box_end|>')",
    #     "right_single(start_box='<|box_start|>(600,673)<|box_end|>')",
    #     "drag(start_box='<|box_start|>(100,100)<|box_end|>', end_box='<|box_start|>(200,200)<|box_end|>')",
    #     "hotkey(key='ctrl+t')",
    #     "type(content='Hello, World!\\n')",
    #     "scroll(start_box='<|box_start|>(400,400)<|box_end|>', direction='down')",
    #     "wait()"
    # ]

    # json_result = action_space_to_keymousego(actions)
    # json_script = json.loads(json_result)  # 解析 JSON
    # for entry in json_script:
    #     print(entry)
    # action_space_result = keymousego_to_action_space(json_script)
    # for action in action_space_result:
    #     print(action)
