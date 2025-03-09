import json
import pyautogui
from loguru import logger
import os
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from agent_partially_connected.prompts import *

# action space 的坐标范围是默认0-1000，keymousego的坐标范围是0-1

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


def script_to_sharegpt(script, instruction):
    actions, imgs = keymousego_to_action_space(script)
    messages = []
    for action, img in zip(actions, imgs):
        messages.append(
            {
                "content": "<image>",
                "role": "user"    
            }
        )
        messages.append({
                "content": action,
                "role": "assistant"
            })
    messages[0]['content'] = messages[0]['content'] + SYS_CODE_UITARS_COMPUTER.format(language="Chinese", instruction=instruction)
    return messages, imgs

if __name__ == "__main__":

    # 示例 JSON 脚本
    json_script = [
        [735,"EM","mouse move",["0.3380208333333333%","0.45740740740740743%"]],
        [1270,"EM","mouse move",["0.3375%","0.45740740740740743%"]],
        [200,"EM","mouse move",["0.33645833333333336%","0.6981481481481482%"]],
        [200,"EM","mouse move",["0.35833333333333334%","0.7925925925925926%"]],
        [550,"EM","mouse left down",["0.3614583333333333%","0.8111111111111111%"],"scripts\\0304_1114\\screenshot_mouse_left_down_20250304_111443_209482.png"],
        [104,"EM","mouse left up",["0.3614583333333333%","0.8111111111111111%"],"scripts\\0304_1114\\screenshot_mouse_left_up_20250304_111443_313062.png"],
        [1037,"EM","mouse move",["0.3614583333333333%","0.8111111111111111%"]],
        [200,"EM","mouse move",["0.39895833333333336%","0.8092592592592592%"]],
        [201,"EM","mouse move",["0.5223958333333333%","0.8944444444444445%"]],
        [221,"EM","mouse move",["0.5567708333333333%","0.9666666666666667%"]],
        [200,"EM","mouse move",["0.5510416666666667%","0.9675925925925926%"]],
        [140,"EM","mouse left down",["0.5494791666666666%","0.9675925925925926%"],"scripts\\0304_1114\\screenshot_mouse_left_down_20250304_111445_313748.png"],
        [91,"EM","mouse left up",["0.5494791666666666%","0.9675925925925926%"],"scripts\\0304_1114\\screenshot_mouse_left_up_20250304_111445_404774.png"],
        [819,"EM","mouse move",["0.5494791666666666%","0.9675925925925926%"]],
        [205,"EM","mouse move",["0.5385416666666667%","0.8453703703703703%"]],
        [418,"EM","mouse move",["0.5380208333333333%","0.8435185185185186%"]],
        [261,"EM","mouse move",["0.5442708333333334%","0.962037037037037%"]],
        [252,"EM","mouse left down",["0.54375%","0.9638888888888889%"],"scripts\\0304_1114\\screenshot_mouse_left_down_20250304_111447_359415.png"],
        [98,"EM","mouse left up",["0.54375%","0.9638888888888889%"],"scripts\\0304_1114\\screenshot_mouse_left_up_20250304_111447_459986.png"],
        [450,"EM","mouse move",["0.54375%","0.9638888888888889%"]],
        [201,"EM","mouse move",["0.5489583333333333%","0.95%"]],
        [200,"EM","mouse move",["0.6625%","0.8740740740740741%"]],
        [201,"EM","mouse move",["0.7041666666666667%","0.9416666666666667%"]],
        [523,"EM","mouse move",["0.7078125%","0.9657407407407408%"]],
        [303,"EM","mouse move",["0.7088541666666667%","0.9657407407407408%"]],
        [149,"EM","mouse left down",["0.709375%","0.9657407407407408%"],"scripts\\0304_1114\\screenshot_mouse_left_down_20250304_111449_483242.png"],
        [111,"EM","mouse left up",["0.7098958333333333%","0.9657407407407408%"],"scripts\\0304_1114\\screenshot_mouse_left_up_20250304_111449_594811.png"],
        [258,"EM","mouse move",["0.7098958333333333%","0.9657407407407408%"]],
        [200,"EM","mouse move",["0.5197916666666667%","0.7407407407407407%"]],
        [200,"EM","mouse move",["0.35052083333333334%","0.4675925925925926%"]],
        [201,"EM","mouse move",["0.33541666666666664%","0.44074074074074077%"]],
]

    # 转换并打印结果
    messages, imgs = script_to_sharegpt(json_script, "请在屏幕上点击左键")
    for message, img in zip(messages, imgs):
        print(message)
        print(img)
    
    




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
