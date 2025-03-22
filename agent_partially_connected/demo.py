import os
from agent import *

from utils import *
from excutor import *
from PIL import ImageGrab

from loguru import logger




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
    instruction = "copy the first line and paste in the last line."


    success = False
    while not success:
        subtask_success = False
        img = ImageGrab.grab()
        subtask = planner.inference_subtask(instruction, img=img)
        while not subtask_success:
            action = coder.output_action(subtask, img=img)
            try:
                feedback = parse_and_execute_output(action)
                if "finished()" in feedback:
                    subtask_success = True
            except Exception as e:
                logger.error(f"Execute Action Error: {str(e)}")
                print(e.__traceback__.tb_frame.f_globals["__file__"])   # 发生异常所在的文件
                print(e.__traceback__.tb_lineno)                        # 发生异常所在的行数
            logger.info(f"Subtask Success: {subtask_success}")
        coder.reset()

        success = planner.detect(instruction, img)
        logger.info(f"Success: {success}")
            



