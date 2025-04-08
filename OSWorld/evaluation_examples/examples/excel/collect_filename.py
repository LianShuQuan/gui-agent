import os
import json # 导入 json 模块

# 获取当前目录下的所有文件和文件夹名称
all_items = os.listdir('.')

# 初始化一个空列表来存储提取出的文件名
json_filenames = []

# 遍历所有项目
for item in all_items:
    # 检查项目是否是一个文件并且以 .json 结尾
    if os.path.isfile(item) and item.endswith('.json'):
        # 提取文件名（不含 .json 后缀）
        base_name = os.path.splitext(item)[0]
        # 将提取出的文件名添加到列表中
        json_filenames.append(base_name)

# 使用 json.dumps 将列表转换为 JSON 格式的字符串（默认使用双引号）
# 然后打印这个字符串
print(json.dumps(json_filenames))