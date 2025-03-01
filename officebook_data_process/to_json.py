import json
import re

def process_text_to_json(text):
    # 初始化结果列表
    result = []
    
    # 使用正则来匹配以 # 开头的段落
    sections = re.split(r'(?=#)', text)  # 以 # 作为分隔符拆分文本

    for section in sections:
        # 如果分割后的部分不为空且以 # 开头（即为我们需要的段落）
        if section.strip().startswith('#'):
            lines = section.strip().split("\n")  # 将每个段落按行分割
            
            # 第一行是标题（# 开头），其余是内容
            title = lines[0].strip()
            content = "\n".join(lines[1:]).strip()

            # 查找图片路径
            image_paths = re.findall(r'!\[.*?\]\((.*?)\)', content)

            # 如果找到图片路径，先把内容中的图片部分移除
            content_without_images = re.sub(r'!\[.*?\]\((.*?)\)', '<image>', content).strip()

            # 生成消息
            message = {
                "messages": [
                    {
                        "content": title,
                        "role": "user"
                    },
                    {
                        "content": content_without_images,
                        "role": "assistant"
                    }
                ]
            }

            message["images"] = image_paths
            result.append(message)
    
    return result

with open('filtered_file.md', 'r', encoding='utf-8') as file:
    text = file.read()

# 将文本处理成 JSON 格式
json_result = process_text_to_json(text)

with open("officebook_data.json", "w", encoding="utf-8") as output_file:
    json.dump(json_result, output_file, indent=2, ensure_ascii=False)

