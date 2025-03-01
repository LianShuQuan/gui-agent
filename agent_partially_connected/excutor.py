import pyautogui
import time
import ast  # 解析字符串格式的列表
import logging
import sys

def get_center(box_str):
    """解析 start_box 或 end_box 并计算中心坐标"""
    try:
        box = ast.literal_eval(box_str)  # 把字符串 '[x1, y1, x2, y2]' 转成列表
        if len(box) == 4:
            x1, y1, x2, y2 = box
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            return center_x, center_y
        elif len(box) == 2:
            return box
    except:
        logging.error(f"❌ 无效的 box 格式: {box_str}")
    return None, None



import pyautogui

def rescale_coords(x, y, model_coord_width=1000, model_coord_height=1000):
    """
    将模型坐标 (x, y) 缩放到屏幕分辨率范围内
    :param x: 模型输出的 X 坐标
    :param y: 模型输出的 Y 坐标
    :param model_range: 模型坐标的范围，默认是 (1, 1000)
    :return: 缩放后的屏幕坐标 (screen_x, screen_y)
    """
    # 获取当前屏幕分辨率
    screen_width, screen_height = pyautogui.size()

    # 计算缩放比例
    scale_x = screen_width / model_coord_width
    scale_y = screen_height / model_coord_height

    # 应用缩放
    screen_x = int(x * scale_x)
    screen_y = int(y * scale_y)

    return screen_x, screen_y



def execute_action(action):
    """
    解析并执行 action，例如：
    click(start_box='[100, 200, 150, 250]') → 在中心点点击
    """
    if action.startswith("click"):
        start_box = action.split("start_box=")[1].strip(" '()")
        x, y = get_center(start_box)
        if x is not None:
            pyautogui.click(rescale_coords(x, y))

    elif action.startswith("left_double"):
        start_box = action.split("start_box=")[1].strip(" '()")
        x, y = get_center(start_box)
        if x is not None:
            pyautogui.doubleClick(rescale_coords(x, y))

    elif action.startswith("right_single"):
        start_box = action.split("start_box=")[1].strip(" '()")
        x, y = get_center(start_box)
        if x is not None:
            pyautogui.rightClick(x, y)

    elif action.startswith("drag"):
        start_part = action.split("start_box=")[1].split(", end_box=")[0].strip(" '()")
        end_part = action.split("end_box=")[1].strip(" '()")
        x1, y1 = get_center(start_part)
        x2, y2 = get_center(end_part)
        if x1 is not None and x2 is not None:
            pyautogui.moveTo(rescale_coords(x1, y1))
            pyautogui.dragTo(rescale_coords(x2, y2), duration=0.5, button="left")

    elif action.startswith("scroll"):
        start_box = action.split("start_box=")[1].split(", direction=")[0].strip(" '()")
        direction = action.split("direction=")[1].strip(" '()")
        x, y = get_center(start_box)
        if x is not None:
            pyautogui.moveTo(rescale_coords(x, y))
            scroll_amount = 100 if direction.lower() in ["up", "right"] else -100
            pyautogui.scroll(scroll_amount)

    elif action.startswith("hotkey"):
        key = action.split("key=")[1].strip(" '()")
        keys = key.split(" ")
        if sys.platform.startswith('darwin'):
            keys = [key.replace("ctrl", "command") for key in keys]
            pyautogui.hotkey(*keys, interval=0.25)
        pyautogui.hotkey(*keys)

    elif action.startswith("type"):
        content = action.split("content=")[1].strip(" '()")
        pyautogui.write(content, interval=0.05)

    elif action.startswith("wait"):
        time.sleep(1)

    elif action.startswith("finished"):
        return "finished()"

    elif action.startswith("call_user"):
        print("User intervention required!")
        input("Press Enter to continue...")

# # 示例调用
# actions = [
#     "click(start_box='[300, 200, 350, 250]')",
#     "left_double(start_box='[250, 250, 280, 280]')",
#     "right_single(start_box='[400, 400, 420, 420]')",
#     "type(content='Hello, World!\\n')",
#     "hotkey(key='ctrl+c')",
#     "scroll(start_box='[400, 500, 450, 550]', direction='down')",
#     "drag(start_box='[100, 100, 120, 120]', end_box='[200, 200, 220, 220]')",
#     "Wait()",
#     "Finished()"
# ]

# for action in actions:
#     result = execute_action(action)
#     if result == "Finished":
#         break


def parse_and_execute_output(output_str):
    """
    解析模型输出，并执行 `Action:` 后的每个操作
    """
    # 分割文本，获取 `Action:` 后的内容
    if "Action:" in output_str:
        actions_str = output_str.split("Action:")[1].strip()  # 获取 Action 部分
        actions = actions_str.split("\n")  # 如果有多行，将它们拆分为单独的 action
        
        for action in actions:
            action = action.strip()  # 去掉多余空格
            if action:  # 确保不为空行
                logging.info(f"Executing action: {action}")
                return execute_action(action)
            else:
                logging.error("❌ 空的 action")
    else:
        logging.error("❌ 没有找到 Action 部分！")


# 示例调用
# output_str = """
# Action:
# click(start_box='(37,56)')
# """

# parse_and_execute_output(output_str)    