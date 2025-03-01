from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from typing import *
import base64
import requests
import re
import os
from PIL import Image
from io import BytesIO

# point (str) -> point
def pred_2_point(s):
    floats = re.findall(r'-?\d+\.?\d*', s)
    floats = [float(num) for num in floats]
    if len(floats) == 2:
        click_point = floats
    elif len(floats) == 4:
        click_point = [(floats[0]+floats[2])/2, (floats[1]+floats[3])/2]
    return click_point



def qwen2generate(model: Qwen2VLForConditionalGeneration, processor: AutoProcessor, messages: List[dict]):
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to("cuda")
    generated_ids = model.generate(**inputs, max_new_tokens=1000)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0]

    return output_text



def to_base64_openai_format(image: Union[str, Image.Image], format: Optional[str] = 'PNG') -> str:
    if isinstance(image, str):
        with open(image, "rb") as image_file:
            return f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode()}"
    elif isinstance(image, Image.Image):
        buffer = BytesIO()
        image.save(buffer, format=format)
        return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}"
  


def image_to_base64_format_with_compress(image:Image.Image, max_size_mb=4.8, format='PNG'):
    """
    压缩图片使其小于指定大小
    image: PIL Image对象
    max_size_mb: 最大大小（MB）
    返回: base64字符串
    """
    # 初始质量
    quality = 95
    # 初始缓冲区
    buffer = BytesIO()
    
    while True:
        # 清空缓冲区
        buffer.seek(0)
        buffer.truncate()
        
        # 保存图片到缓冲区
        image.save(buffer, format=format, quality=quality)
        
        # 获取当前大小
        size_mb = len(buffer.getvalue()) / (1024 * 1024)
        
        # 如果小于最大大小，跳出循环
        if size_mb <= max_size_mb:
            break
            
        # 否则降低质量继续尝试
        quality -= 5
        
        # 如果质量已经很低但仍然太大，则调整图片尺寸
        if quality < 20:
            width, height = image.size
            image = image.resize((int(width*0.8), int(height*0.8)), Image.LANCZOS)
            quality = 95
    
    # 转换为base64
    base64_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{base64_str}"

