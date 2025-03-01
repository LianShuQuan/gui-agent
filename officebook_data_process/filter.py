
import re

# 从文件读取内容（确保文件路径正确）
with open('/Users/lianshuquan/Downloads/data/office_book/output/MicrosoftWord2019StepbyStep/auto/MicrosoftWord2019StepbyStep.md', 'r', encoding='utf-8') as file:
    filtered_text = file.read()


def delete_lines(text, n, m):
    lines = text.split('\n')
    
    # 获取第 n 到第 m 行之间的内容
    result_lines = lines[n-1:m]
    
    # 将这些行合并为一个新的文本
    result_text = '\n'.join(result_lines)
    
    return result_text

filtered_text = delete_lines(filtered_text, 165, 10728)

# 使用正则表达式删除  段落及其内容
filtered_text = re.sub(r'# See Also.*?(?=\n#|\Z)', '', filtered_text, flags=re.DOTALL)
filtered_text = re.sub(r'# PRACTICE TASKS.*?(?=\n#|\Z)', '', filtered_text, flags=re.DOTALL)
filtered_text = re.sub(r'# Part.*?(?=\n#|\Z)', '', filtered_text, flags=re.DOTALL)
filtered_text = re.sub(r'# Appendix.*?(?=\n#|\Z)', '', filtered_text, flags=re.DOTALL)
filtered_text = re.sub(r'# Glossary.*?(?=\n#|\Z)', '', filtered_text, flags=re.DOTALL)
filtered_text = re.sub(r'# In this chapter.*?(?=\n#|\Z)', '', filtered_text, flags=re.DOTALL)
filtered_text = re.sub(r'# Important.*?(?=\n#|\Z)', '', filtered_text, flags=re.DOTALL)
filtered_text = re.sub(r'# 4.Storage.*?(?=\n#|\Z)', '', filtered_text, flags=re.DOTALL)
filtered_text = re.sub(r'# Or.*?(?=\n#|\Z)', '', filtered_text, flags=re.DOTALL)






# 使用正则表达式过滤掉 # xxx 段落中没有内容的段落
filtered_text = re.sub(r'# [^\n]+\n\s*(?=#|\Z)', '', filtered_text)




# 将结果写入新的文件中
with open('filtered_file.md', 'w', encoding='utf-8') as output_file:
    output_file.write(filtered_text)

