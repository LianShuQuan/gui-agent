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
logger.add(sys.stderr, level='INFO')  # 只输出警告以上的日志


if __name__ == "__main__":

    coder = UITars(config_name="coder")

    coder.output_action("新建一个python文件。", img=ImageGrab.grab())
            



