import os
from agent import *
import logging
from utils import *
from excutor import *
from PIL import ImageGrab

logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    time.sleep(2)
    qwen_path = "Qwen/Qwen2-VL-2B-Instruct"
    coder_model_path = "bytedance-research/UI-TARS-7B-DPO"
    planner_model = "Qwen/Qwen2-VL-72B-Instruct"
    siliconflow_api_key = "sk-bbwqnimupumnxffvokuqwwaruvdkavfmwobugvqgxwujhdfq"
    siliconflow_api_base = "https://api.siliconflow.cn/v1"
    # coder = Coder(local=True, qwen_path=qwen_path, model_path=coder_model_path)
    coder = UITars(llm_api_base="http://localhost:8000/v1", llm_api_key="sk-xxx", llm_model="UI-TARS-7B-DPO")
    # detect_agent = DetectionAgent(local=True, qwen_path=qwen_path, model_path=coder_model_path)
    # detect_agent = DetectionAgent(llm_api_base="http://localhost:8000/v1", llm_api_key="sk-xxx", llm_model="UI-TARS-7B-DPO")
    detect_agent = DetectionAgent(llm_api_base=siliconflow_api_base, llm_api_key=siliconflow_api_key, llm_model="Qwen/Qwen2-VL-72B-Instruct")
    planner = Planner(llm_model=planner_model, llm_api_key=siliconflow_api_key, llm_api_base=siliconflow_api_base)

    instruction = "copy the first line and paste in the last line."
    image_path = "/Users/lianshuquan/github_repo/agent_partially_connected/demo/word.png"
    # img_base64 = image_to_base64_format_with_compress(Image.open(image_path), max_size_mb=0.3)
    # img_base64 = to_base64_openai_format(image_path)

    success = False
    while not success:
        subtask_success = False
        img_base64 = to_base64_openai_format(ImageGrab.grab())
        subtask = planner.inference_subtask(instruction, img_path=img_base64)
        while not subtask_success:
            action = coder.output_action(subtask, img_path=img_base64)
            try:
                feedback = parse_and_execute_output(action)
                if "finished()" in feedback:
                    subtask_success = True
                else:
                    planner.add_subtask_history("subtask excuted")
            except Exception as e:
                logging.error(f"Execute Action Error: {str(e)}")
                print(e.__traceback__.tb_frame.f_globals["__file__"])   # 发生异常所在的文件
                print(e.__traceback__.tb_lineno)                        # 发生异常所在的行数
                planner.add_subtask_history(f"Execute Action Error: {str(e)}")
            logging.info(f"Subtask Success: {subtask_success}")
        coder.reset()
        detect_agent.sync_history(planner.history)
        success = detect_agent.detect(instruction, img_base64)
        logging.info(f"Success: {success}")
            



