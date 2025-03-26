import os
from agent import *

from utils import *
from excutor import *
from PIL import ImageGrab

from loguru import logger

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

logger.remove()  # 这行很关键，先删除logger自动产生的handler，不然会出现重复输出的问题
logger.add(sys.stderr, level='DEBUG')  # 只输出警告以上的日志


def str_match(str1: str, str2: str) -> bool:
    return str1.lower() in str2.lower() or str2.lower() in str1.lower()


if __name__ == "__main__":
    time.sleep(2)
    qwen_path = "Qwen/Qwen2-VL-2B-Instruct"
    coder_model_path = "bytedance-research/UI-TARS-7B-DPO"
    planner_model = "Qwen/Qwen2-VL-72B-Instruct"
    siliconflow_api_key = "sk-bbwqnimupumnxffvokuqwwaruvdkavfmwobugvqgxwujhdfq"
    siliconflow_api_base = "https://api.siliconflow.cn/v1"
    local_api_base = "http://localhost:8000/v1"

    # coder = UITars(agent_name="coder", mllm=ApiMLLM(model_name="UI-TARS-7B-DPO", base_url=local_api_base, api_key="sk-xxx"))
    # detect_agent = DetectionAgent(agent_name="detect", mllm=ApiMLLM(base_url=siliconflow_api_base, api_key=siliconflow_api_key))
    # planner = Planner(agent_name="planner", mllm=ApiMLLM(model_name=planner_model, base_url=siliconflow_api_base, api_key=siliconflow_api_key))
    coder = UITars(config_name="coder")

    planner = Planner()
    instruction = "分步把ppt里每一个页的“your logo”删除。"


    success = False
    while not success:
        subtask_success = False
        img = ImageGrab.grab()
        subtask = planner.inference_subtask(instruction, img=img)
        if str_match(subtask, "Task completed"):
            success = True
        while not subtask_success:
            action = coder.output_action(subtask, img=img)
            try:
                feedback = parse_and_execute_output(action)
                if feedback and "finished()" in feedback:
                    subtask_success = True
            except Exception as e:
                logger.error(f"Execute Action Error: {str(e)}")
                print(e.__traceback__.tb_frame.f_globals["__file__"])   # 发生异常所在的文件
                print(e.__traceback__.tb_lineno)                        # 发生异常所在的行数
            logger.info(f"Subtask Success: {subtask_success}")
        coder.reset()

        # success = planner.detect(instruction, img)
        # logger.info(f"Success: {success}")
            



