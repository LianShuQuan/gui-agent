import json
import pyautogui
import logging

# action space 的坐标范围是默认0-1000，keymousego的坐标范围是0-1

def action_coord2keymousego_str(x, y, model_coord_width=1000, model_coord_height=1000):
    
    rel_x = x / model_coord_width
    rel_y = y / model_coord_height
    return f"{rel_x:.5f}%", f"{rel_y:.5f}%"

def action_space_to_keymousego(actions):
    """将 action space 指令转换为 JSON 脚本格式"""
    json_script = []
    last_time = 0  # 记录上一个动作的时间
    
    for action in actions:
        if action.startswith("click") or action.startswith("left_double") or action.startswith("right_single"):
            action_type = "mouse left down" if "click" in action else "mouse right down" if "right_single" in action else "mouse left down"
            start_box = action.split("start_box='<|box_start|>(")[1].split(")<|box_end|>'")[0]
            x, y = map(int, start_box.split(","))
            rel_x, rel_y = action_coord2keymousego_str(x, y)

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
            rel_x1, rel_y1 = action_coord2keymousego_str(x1, y1)
            rel_x2, rel_y2 = action_coord2keymousego_str(x2, y2)

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
            rel_x, rel_y = action_coord2keymousego_str(x, y)
            action_type = "mouse wheel up" if direction == "up" else "mouse wheel down"
            json_script.append([last_time, "EM", action_type, [rel_x, rel_y]])

        elif action.startswith("wait"):
            json_script.append([5000, "EX", "wait", ""])

        last_time = 100  # 每个动作默认间隔 100ms

    return json.dumps(json_script, indent=4, ensure_ascii=False)



import logging

def keymousego_to_action_space(script, model_coord_width=1000, model_coord_height=1000):
    """
    将脚本转换为 action space 代码。
    
    :param script: 操作序列
    :param model_coord_width: action space 的坐标范围 (默认 1000)
    :param model_coord_height: action space 的坐标范围 (默认 1000)
    :return: 转换后的 action space 代码
    """
    actions = []
    
    # 处理时间间隔
    last_action = None
    double_click_count = 0

    for i in range(len(script)):
        if double_click_count > 0:
            double_click_count -= 1
            continue

        entry = script[i]
        wait_time, action_type, action, params = entry

        if wait_time >= 5000:  # 如果超过5s，插入 wait()
            actions.append("wait()")

        if action_type == "EM":  # 处理鼠标操作
            x, y = [int(float(coord.strip("%")) * model_coord_width) for coord in params]

            # 识别鼠标左键双击
            if action == "mouse left down" and i + 3 < len(script):
                next1 = script[i + 1]
                next2 = script[i + 2]
                next3 = script[i + 3]
                if (next1[0] + next2[0] + next3[0]) > 700:
                    logging.error(f"❌ 双击间隔过长：{entry}, {next1}, {next2}, {next3}")
                if next1[3]!=params or next2[3]!=params or next3[3]!=params:
                    logging.error(f"❌ 双击坐标不一致：{entry}, {next1}, {next2}, {next3}")
                # 确保模式是：down → up → down → up（间隔短时间）
                if (next1[2] == "mouse left up" and next2[2] == "mouse left down" and next3[2] == "mouse left up")\
                    and (next1[0] + next2[0] + next3[0]) < 700\
                    and next1[3] == params and next2[3] == params and next3[3] == params:
                    actions.append(f"left_double(start_box='<|box_start|>({x},{y})<|box_end|>')")
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
                elif last_action[0] == "left_down":
                    actions.append(f"click(start_box='<|box_start|>({x},{y})<|box_end|>')")
                last_action = None  # 重置

            # 识别鼠标右键单击
            elif action == "mouse right down":
                last_action = ("right", (x, y))

            elif action == "mouse right up" and last_action and last_action[0] == "right":
                actions.append(f"right_single(start_box='<|box_start|>({x},{y})<|box_end|>')")
                last_action = None  # 重置



        elif action_type == "EK":  # 处理键盘操作
            if action == "key down":
                last_key = params[1]
            elif action == "key up" and last_key == params[1]:
                actions.append(f"hotkey(key='{last_key}')")
                last_key = None  # 重置

        elif action_type == "EX":  # 处理输入文本
            if action == "input":
                actions.append(f"type(content='{params}\\n')")

    return actions

if __name__ == "__main__":

    # 示例 JSON 脚本
    json_script = [
        [3000, "EM", "mouse right down", ["0.05208%", "0.1852%"]],
        [50,   "EM", "mouse right up",   ["0.05208%", "0.1852%"]],
        [1000, "EK", "key down",         [70, "F", 0]],
        [50,   "EK", "key up",           [70, "F", 0]],
        [100,  "EM", "mouse left down",  ["0.2604%", "0.4630%"]],
        [100,  "EM", "mouse move",       ["0.2604%", "0.5556%"]],
        [100,  "EM", "mouse left up",    ["0.3125%", "0.5556%"]],
        [100,  "EX", "input",            "你好 world"],
        [100,  "EM", "mouse left down",  ["0.2604%", "0.4630%"]],
        [100,  "EM", "mouse left up",  ["0.2604%", "0.4630%"]],
        [100,  "EM", "mouse left down",  ["0.2604%", "0.4630%"]],
        [100,  "EM", "mouse left up",  ["0.2604%", "0.4630%"]]
    ]

    # 转换并打印结果
    converted_script = keymousego_to_action_space(json_script)
    print(converted_script)




# 示例 Action Space
    actions = [
        "click(start_box='<|box_start|>(101,204)<|box_end|>')",
        "left_double(start_box='<|box_start|>(520,500)<|box_end|>')",
        "right_single(start_box='<|box_start|>(600,673)<|box_end|>')",
        "drag(start_box='<|box_start|>(100,100)<|box_end|>', end_box='<|box_start|>(200,200)<|box_end|>')",
        "hotkey(key='ctrl+t')",
        "type(content='Hello, World!\\n')",
        "scroll(start_box='<|box_start|>(400,400)<|box_end|>', direction='down')",
        "wait()"
    ]

    json_result = action_space_to_keymousego(actions)
    json_script = json.loads(json_result)  # 解析 JSON
    for entry in json_script:
        print(entry)
    action_space_result = keymousego_to_action_space(json_script)
    for action in action_space_result:
        print(action)
