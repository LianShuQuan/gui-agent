import os
from typing import List

from tqdm import tqdm

import torch
from transformers import Qwen2VLForConditionalGeneration
from qwen_vl_utils import process_vision_info
from peft import AutoPeftModelForCausalLM
from transformers.generation import GenerationConfig
from transformers import AutoModelForCausalLM, AutoProcessor
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

from openai import OpenAI
import base64
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO


def calc(processor: AutoProcessor, messages: List[dict]):
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
    print(inputs["input_ids"].shape[1])

# 加载 qwen2vl 的 tokenizer 和 processor（假设是多模态模型）
processor = AutoProcessor.from_pretrained("osunlp/UGround-V1-7B")

# 输入文本
input_text = '''
<image>
Word displays information about the size of a document at the left end of the status bar. To show the number of words in only part of the document, such as a few paragraphs, simply select that part. You can review more statistics and specify the content to include in the statistics in the Word Count dialog box. To open it, select the Word Count indicator on the status bar or the Word Count button in the Proofing group on the Review tab.  

![](images/504a0fb6a3b3b0a27a8e41a2322a89e8683fd1523fb0325bb7b8d6bce666aacb.jpg)  

In addition to counting pages and words, Word counts characters, paragraphs, and lines  

To display synonyms for a word  

Right-click the word, and then select Synonyms.  

o display synonyms, antonyms, and the definition of a word  

Right-click the word, select Synonyms, and then on the submenu, select Thesaurus. Select the word. Then do either of the following:  On the Review tab, in the Proofing group, select the Thesaurus button.  Press Shift $\mathbf{\nabla}+\mathbf{F}\mathbf{7}$ .  

To replace a word with a synonym  

Display the list of synonyms, and then select the synonym you want to use. Display the Thesaurus pane, point to the synonym you want to use, select the arrow that appears, and then select Insert.  

To change the languages used by the translator tool  

1. On the Review tab, in the Language group, select Translate, and then select Set Document Translation Language to display the Translator pane. 2. In the Translator pane, from the Selection or Document page, do the following: 1. In the From list, select the original language. 2. In the To list, select the translation language.  

To translate text within Word  

1. Select the word or phrase you want to translate.   
2. On the Review tab, in the Language group, select Translate, and then select Translate Selection to open the Translator pane.   
3. The From and To boxes display the currently selected original and translation languages. If either language is incorrect, you can change it.   
4. If you want to replace the selected text with the translation, select Insert.  

To translate a word or phrase that does not appear in the text of a document  

1. In the Translate pane, in the From box, enter the word or phrase you want to translate.   
2. Microsoft Translator automatically detects the language. If the detected language is incorrect, in the From list, select the original language of the text you want to translate.   
3. In the To list, select the language to which the text should be translated.   
4. If you want to insert the translated text at the location of your cursor, select Insert.  

# To translate an entire document  

1. Open the document you want to translate in Word.   
2. On the Review tab, in the Language group, select Translate, and then select Translate Document.   
3. On the Document page of the Translator pane, confirm or change the From and To languages, and then select Translate. Word creates a translation of the document in a new file. 
'''

# 输入图像
image_path = "/Users/lianshuquan/github_repo/agent_partially_connected/images/0a43c9080e13aec17454f3ce5cbdd0e5e76c0fd4bc3b5c1ed226bf730ed8719b.jpg"  # 替换为你的图像路径
image = Image.open(image_path)


messages = [
        {
            "role": "user",
            "content": [{'type': 'image', 'image': image_path},
                {'type': 'text', 'text': input_text}],
        }]

calc(processor,messages)


