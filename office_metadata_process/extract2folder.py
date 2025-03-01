import zipfile
import os
from pathlib import Path
from folder2office_file import create_office_file_with_type_detection

def extract_office_file(file_path, output_dir=None):
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return "文件不存在"
    
    # 获取文件名和扩展名
    file_name = Path(file_path).stem
    ext = Path(file_path).suffix.lower()
    
    # 检查文件扩展名
    if ext not in ['.docx', '.pptx', '.xlsx']:
        return "不支持的文件格式"
    
    # 如果没有指定输出目录，则在原文件同级目录创建
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(file_path), f"{file_name}_extracted")
    
    try:
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 解压缩文件
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # 获取所有文件列表
            file_list = zip_ref.namelist()
            
            # 解压所有文件
            for file in file_list:
                # 创建必要的子目录
                if file.endswith('/'):
                    os.makedirs(os.path.join(output_dir, file), exist_ok=True)
                    continue
                    
                # 确保目标目录存在
                os.makedirs(os.path.dirname(os.path.join(output_dir, file)), exist_ok=True)
                
                # 提取文件
                with zip_ref.open(file) as source:
                    with open(os.path.join(output_dir, file), 'wb') as target:
                        target.write(source.read())
            
        return output_dir
            
    except Exception as e:
        return f"解压文件出错: {str(e)}"

# 使用示例
if __name__ == "__main__":
    # 替换为你的文件路径
    file_path = "/Users/lianshuquan/github_repo/OSWorld/assets/docx/04 CHIN9505 EBook Purchasing info 2021 Jan.docx"
    
    # 可以指定输出目录（可选）
    # output_dir = "custom_output_path"
    
    # 解压文件
    output_dir = extract_office_file(file_path)
    # print(result)


    # 将文件夹转换为office文件
    result = create_office_file_with_type_detection(output_dir)
    print(result)
