import requests
import re
from bs4 import BeautifulSoup
from loguru import logger
import os
from datetime import datetime
from urllib.parse import urljoin

def clean_html(url):
    # 获取HTML页面内容
    response = requests.get(url)
    html_content = response.text

    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # 筛选出所有class为"ocpArticleContent"的article元素
    articles = soup.select('article.ocpArticleContent')
    logger.info(f"找到 {len(articles)} 个文章元素")
    if len(articles) == 0:
        logger.error("没有找到文章元素")
        return

    title_sections = soup.select("header.ocpArticleTitleSection")
    logger.info(f"找到 {len(title_sections)} 个标题元素")
    if len(title_sections) == 0:
        logger.error("没有找到标题元素")
        return
    h1_element = title_sections[0].find('h1')
    if h1_element:
        title_text = h1_element.text.strip()
        logger.info(f"提取到标题: {title_text}")

    # 整合为简单的html并保存到本地
    new_html = BeautifulSoup("<html><head><meta charset='utf-8'></head><body></body></html>", 'html.parser')

    # 添加标题
    if title_sections:
        for title_section in title_sections:
            new_html.body.append(title_section)

    # 添加文章内容
    if articles:
        for article in articles:
            new_html.body.append(article)

    # 添加基本样式
    style_tag = new_html.new_tag('style')
    style_tag.string = """
    body {
        font-family: Arial, sans-serif;
        line-height: 1.6;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    img {
        max-width: 100%;
        height: auto;
    }
    """
    new_html.head.append(style_tag)

    # 处理标题文本，创建安全的文件名
    def create_safe_filename(text, max_length=150):
        # 移除不允许用于文件名的字符
        safe_text = re.sub(r'[\\/*?:"<>|]', "", text)
        # 替换空格为下划线
        safe_text = safe_text.replace(' ', '_')
        # 限制长度
        if max_length and len(safe_text) > max_length:
            safe_text = safe_text[:max_length]
        # 确保文件名不为空
        if not safe_text:
            safe_text = "article"
        return safe_text

    # 生成文件名
    filename = f"{title_text}.html"
    filename = create_safe_filename(filename)
    # 保存到本地
    with open(filename, "w", encoding="utf-8") as file:
        file.write(str(new_html.prettify()))

    logger.info(f"文章已保存为: {os.path.abspath(filename)}")


def find_useful_urls(url):
    # 获取HTML页面内容
    response = requests.get(url)
    html_content = response.text

    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # 找到所有类似的链接元素 - 这里找"supLeftNavLink"类的链接
    nav_links = soup.select('a.supLeftNavLink')
    logger.info(f"找到 {len(nav_links)} 个导航链接元素")

    # 提取URLs并去重
    urls = set()  # 使用集合自动去重
    base_url = "https://support.microsoft.com/"
    for link in nav_links:
        if 'href' in link.attrs:
            href = link['href']
            # 处理相对URL，转换为绝对URL
            absolute_url = urljoin(base_url, href)
            urls.add(absolute_url)
            
            # 记录链接文本和URL，方便检查
            logger.info(f"链接文本: {link.text.strip()} | URL: {absolute_url}")

    logger.info(f"共找到 {len(urls)} 个唯一URL")
    return list(urls)

if __name__=="__main__":
    # 示例URL
    url = "https://support.microsoft.com/en-us/office/insert-pictures-3c51edf4-22e1-460a-b372-9329a8724344"
    urls = find_useful_urls(url)
    for url in urls:
        # 处理每个URL
        logger.info(f"处理链接: {url}")
        clean_html(url)
