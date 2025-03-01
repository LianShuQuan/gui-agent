import zipfile
import os
from pathlib import Path

def create_office_file(input_dir, output_file=None):
    # 检查输入目录是否存在
    if not os.path.exists(input_dir):
        return "输入目录不存在"
    
    # 如果没有指定输出文件，则根据输入目录名创建
    if output_file is None:
        # 移除目录名中的 "_extracted" 后缀
        dir_name = os.path.basename(input_dir)
        base_name = dir_name.replace('_extracted', '_rebuilt')
        # 默认创建docx文件，也可以根据目录内容判断文件类型
        output_file = os.path.join(os.path.dirname(input_dir), f"{base_name}.docx")
    
    try:
        # 创建ZIP文件
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 遍历目录中的所有文件
            for root, dirs, files in os.walk(input_dir):
                for file in files:
                    # 获取文件的完整路径
                    file_path = os.path.join(root, file)
                    # 计算归档路径（相对路径）
                    archive_path = os.path.relpath(file_path, input_dir)
                    
                    # 添加文件到ZIP
                    zip_file.write(file_path, archive_path)
                
                # 添加空目录
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    archive_path = os.path.relpath(dir_path, input_dir) + '/'
                    zif = zipfile.ZipInfo(archive_path)
                    zip_file.writestr(zif, '')
        
        return output_file
            
    except Exception as e:
        return f"创建文件出错: {str(e)}"

def detect_office_type(input_dir):
    """
    通过检查目录内容来判断Office文档类型
    """
    if os.path.exists(os.path.join(input_dir, 'word')):
        return '.docx'
    elif os.path.exists(os.path.join(input_dir, 'ppt')):
        return '.pptx'
    elif os.path.exists(os.path.join(input_dir, 'xl')):
        return '.xlsx'
    return '.docx'  # 默认返回docx

def create_office_file_with_type_detection(input_dir, output_file=None):
    """
    自动检测文件类型并创建相应的Office文件
    """
    if not os.path.exists(input_dir):
        return "输入目录不存在"
    
    # 检测文件类型
    file_ext = detect_office_type(input_dir)
    
    # 如果没有指定输出文件，则根据输入目录名和检测到的类型创建
    if output_file is None:
        dir_name = os.path.basename(input_dir)
        base_name = dir_name.replace('_extracted', '_rebuilt')
        output_file = os.path.join(os.path.dirname(input_dir), f"{base_name}{file_ext}")
    
    return create_office_file(input_dir, output_file)

# 使用示例
if __name__ == "__main__":
    # 替换为你的目录路径
    input_dir = "/Users/lianshuquan/github_repo/PPTAgent/resource/Iphone16Pro copy_extracted"
    
    # 方法1：直接指定输出文件类型
    # result = create_office_file(input_dir, "output.docx")
    
    # 方法2：自动检测文件类型
    result = create_office_file_with_type_detection(input_dir)
    print(result)