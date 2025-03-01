import json
import os
import requests
from pathlib import Path
import glob
import platform
from os.path import expanduser

def get_safe_download_path(original_path, dest_folder):
    """
    获取安全的下载路径
    """

    parts = Path(original_path).parts
    download_dir = os.path.join(dest_folder, parts[-1])

    
    return download_dir

def download_file(url, destination, dest_folder):
    """
    下载文件到指定位置
    """
    try:
        # 获取安全的下载路径
        safe_destination = get_safe_download_path(destination, dest_folder)
        
        # 创建目标文件夹
        os.makedirs(os.path.dirname(safe_destination), exist_ok=True)
        
        # 下载文件
        response = requests.get(url, stream=True)
        response.raise_for_status()  # 检查是否成功
        
        # 写入文件
        with open(safe_destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"文件已下载到: {safe_destination}")
        return True
    except Exception as e:
        print(f"下载失败 {url}: {str(e)}")
        return False

def process_json_files(folder_path, dest_folder):
    """
    处理文件夹中的所有JSON文件
    """
    # 获取所有JSON文件
    json_pattern = os.path.join(folder_path, '**/*.json')
    json_files = glob.glob(json_pattern, recursive=True)
    
    for json_file in json_files:
        try:
            # 读取JSON文件
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否包含config部分
            if 'config' not in data:
                continue
                
            # 遍历config数组
            for config in data['config']:
                if config['type'] == 'download' and 'parameters' in config:
                    # 处理文件下载
                    for file_info in config['parameters'].get('files', []):
                        if 'url' in file_info and 'path' in file_info:
                            # 处理Google Drive链接
                            url = file_info['url']
                            if 'drive.google.com' in url:
                                # 提取文件ID并构造下载链接
                                file_id = url.split('id=')[1].split('&')[0]
                                url = f"https://drive.google.com/uc?id={file_id}&export=download"
                            
                            print(f"正在下载: {url} 到 {file_info['path']}")
                            download_file(url, file_info['path'], dest_folder)
                            
        except Exception as e:
            print(f"处理文件 {json_file} 时出错: {str(e)}")

# 使用示例
if __name__ == "__main__":
    # 替换为你的JSON文件所在文件夹路径
    folder_path = "/Users/lianshuquan/github_repo/OSWorld/evaluation_examples/examples/libreoffice_calc"
    process_json_files(folder_path, "/Users/lianshuquan/github_repo/OSWorld/assets/xlsx")