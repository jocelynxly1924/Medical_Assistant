from typing import List

from states.states import PublicState
import requests
from bs4 import BeautifulSoup
import time
from langchain_core.tools import tool

@tool
def get_medicine_info_tool(medicine_name: str, target_fields: List[str]):
    """搜索中国医药信息查询平台，返回药品括简介、成分、功效、用法、注意事项等内容。

    Args:
        medicine_name: 药品名称（中文或英文）
        target_fields: 需要查询的内容，为以下取值的子集：
            ['介绍','成分','性状','主要功效','适应病症','临床应用及指南','规格','药理作用','药性分解/方解',
            '用法用量','不良反应','禁忌','注意事项','药物相互作用','贮藏方法','有效期','执行标准','附注']

    Returns:
        药品的详细信息，包含药品名称和查询内容"""
    yellow = '\033[93m'
    reset = '\033[0m'
    print(f"{yellow}正在查询药品信息……{reset}")
    search_url = f"https://www.dayi.org.cn/search?keyword={medicine_name}&type=medical"
    medicine_info = get_first_drug_info(search_url)
    content_dict = {}
    for field in medicine_info.get('content', {}):
        if field in target_fields:
            content_dict[field] = medicine_info['content'][field]
    medicine_info_related ={
        'name': medicine_info.get('name','None'),
        'content': content_dict
    }
    return medicine_info_related



def get_first_drug_info(search_url):
    """
    从搜索URL获取第一条药品链接，并返回包含药品名称和详细信息的字典
    返回格式: {'name': '药品名称', 'content': {'标题1': '段落1', '标题2': '段落2', ...}}
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # --- 第一步：处理搜索页，获取第一条药品详情页的链接 ---
    search_response = requests.get(search_url, headers=headers)
    search_response.encoding = 'utf-8'
    search_soup = BeautifulSoup(search_response.text, 'html.parser')

    # 找到第一个药品详情页的链接
    first_link = None
    all_links = search_soup.find_all('a', href=True)
    for link in all_links:
        if '/drug/' in link['href']:
            first_link = link['href']
            break

    if not first_link:
        print("未在搜索页找到药品链接")
        return {'name': None, 'content': {}}

    # 拼接完整的URL
    if first_link.startswith('http'):
        drug_url = first_link
    else:
        drug_url = requests.compat.urljoin('https://www.dayi.org.cn', first_link)

    # --- 第二步：进入药品详情页，提取内容 ---
    print(f"药品详情页: {drug_url}")
    time.sleep(2)
    drug_response = requests.get(drug_url, headers=headers)
    drug_response.encoding = 'utf-8'

    drug_soup = BeautifulSoup(drug_response.text, 'html.parser')

    # 提取药品名称
    name_tag = drug_soup.find('h1')
    drug_name = name_tag.get_text(strip=True) if name_tag else "未找到名称"

    info_dict = {}
    info_dict['name'] = drug_name

    # 用于存储标题和对应内容的字典
    content_dict = {}

    # --- 提取介绍部分（简介和基本属性）---
    intro_parts = []

    # 提取简介段落（p class="intro"）
    intro_paragraph = drug_soup.find('p', class_='intro')
    if intro_paragraph:
        intro_text = intro_paragraph.get_text(strip=True)
        if intro_text:
            intro_parts.append(intro_text)

    # 提取六个基本属性（通用名称、汉语拼音等）
    # 找到所有short-field-item容器
    field_items = drug_soup.find_all('div', class_='short-field-item')
    if field_items:

        for item in field_items:
            # 提取标题
            title_elem = item.find('p', class_='short-field-title')
            # 提取内容
            content_elem = item.find('span', class_='short-field-content')

            if title_elem and content_elem:
                title = title_elem.get_text(strip=True)
                content = content_elem.get_text(strip=True)
                if title and content:
                    intro_parts.append(f"{title}：{content}")

    # 将介绍部分合并存入content_dict
    if intro_parts:
        content_dict['介绍'] = '\n'.join(intro_parts)

    # --- 提取主要标题和段落内容（成分、功能主治等）---
    current_title = None
    current_content = []

    # 按顺序提取所有标题和段落
    content_container = drug_soup.find('div', class_='content') or \
                        drug_soup.find('div', class_='main-content') or \
                        drug_soup.find('div', class_='drug-info') or \
                        drug_soup.find('article') or \
                        drug_soup.body

    if content_container:
        # 获取容器内的所有元素，按顺序处理
        for element in content_container.find_all(['h1', 'h2', 'h3', 'h4', 'p']):
            # 跳过顶层的h1（已经提取了药品名称）
            if element.name == 'h1' and element == name_tag:
                continue

            if element.name in ['h2', 'h3', 'h4']:  # 这是标题
                # 如果之前有正在处理的标题，先保存它
                if current_title and current_content:
                    # 检查是否已经存在相同的标题（避免重复）
                    if current_title not in content_dict:
                        content_dict[current_title] = '\n'.join(current_content)
                    current_content = []

                current_title = element.get_text(strip=True)
                if current_title:  # 只处理非空标题

                    # 硬判断：如果标题是"有效期"或"保质期"，使用专门方法提取
                    if "有效期" in current_title or "保质期" in current_title:
                        expiry_text = extract_expiry_info(element, drug_soup)
                        if expiry_text:
                            # 有效期信息作为特殊段落添加到当前标题下
                            current_content.append(expiry_text)

            elif element.name == 'p':  # 这是段落
                p_text = element.get_text(strip=True)
                # 跳过可能重复的介绍段落（已经在intro中处理过）
                if p_text and len(p_text) > 0:
                    # 检查是否是简介段落（避免重复）
                    if not (intro_paragraph and p_text == intro_paragraph.get_text(strip=True)):
                        if current_title:
                            current_content.append(p_text)
                        else:
                            # 如果没有标题，使用默认标题
                            if "无标题" not in content_dict:
                                content_dict["无标题"] = []
                            content_dict["无标题"].append(p_text)

        # 保存最后一个标题的内容
        if current_title and current_content:
            if current_title not in content_dict:
                content_dict[current_title] = '\n'.join(current_content)

        # 处理无标题的段落（如果有）
        if "无标题" in content_dict:
            # 删除无标题数据
            content_dict.pop("无标题")

    else:
        print("未找到主要内容区域")
        if "错误" not in content_dict:
            content_dict["错误"] = "未找到主要内容区域"

    # 将content_dict存入info_dict
    info_dict['content'] = content_dict

    # print(info_dict)
    return info_dict


def extract_expiry_info(expiry_title_element, drug_soup):
    """
    提取有效期信息并返回文本
    """
    ytime_div = drug_soup.find('div', id='ytime')
    if ytime_div:
        # 找到field-container父级
        container = ytime_div.find_parent('div', class_='field-container')
        if container:
            # 找field-content
            field_content = container.find('div', class_='field-content')
            if field_content:
                expiry_text = field_content.get_text(strip=True)
                return expiry_text
    return None

if __name__ == '__main__':
    # 测试代码
    # info_dict = get_medicine_info_tool(medicine_name="白茅根", target_fields = ["成分","性状","用法用量"])
    info_dict = get_medicine_info_tool.invoke({
        "medicine_name": "板蓝根",
        "target_fields": ["成分", "性状", "用法用量"]
    })
    print(info_dict)