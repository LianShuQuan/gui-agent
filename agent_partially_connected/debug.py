from excutor import *
from agent import *

from loguru import logger

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from actionSpace_KeymouseGo.convert import *
from utils import *



planner_model = "Qwen/Qwen2-VL-72B-Instruct"
siliconflow_api_key = "sk-bbwqnimupumnxffvokuqwwaruvdkavfmwobugvqgxwujhdfq"
siliconflow_api_base = "https://api.siliconflow.cn/v1"
agent = Agent(llm_model=planner_model, llm_api_key=siliconflow_api_key, llm_api_base=siliconflow_api_base)

with open('scripts\\0305_1618\\script.txt', 'r', encoding='utf-8') as f:
    script = f.read()
script = json.loads(script)
script = script[1:]
logger.debug(script)
messages = []
actions, imgs = keymousego_to_action_space(script)
for action, img in zip(actions, imgs):
    messages.append({
            "content": [
                {
                    'type': 'text',
                    'text': action
                },
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': to_base64_openai_format(img)
                    }   
                }
            ],
            "role": "user"    
        })
messages.append({
            "content": "Above is the screenshot and action of a gui agent, what is the agent doing? Only output the task in a sentence. The task is",
            "role": "user"    
        })
response = agent.client.chat.completions.create(
                model=agent.llm_model,
                messages=messages).choices[0].message.content

logger.info(response)

