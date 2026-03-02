# import requests
# from bs4 import BeautifulSoup
# import time
#
# def get_first_drug_info(search_url):
#     """
#     从搜索URL获取第一条药品链接，并打印其详情页内容
#     """
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#     }
#
#     # --- 第一步：处理搜索页，获取第一条药品详情页的链接 ---
#     print("1. 正在获取搜索页...")
#     search_response = requests.get(search_url, headers=headers)
#     search_response.encoding = 'utf-8'
#     search_soup = BeautifulSoup(search_response.text, 'html.parser')
#
#     # 找到第一个药品详情页的链接
#     # 根据你提供的搜索结果页HTML，需要找到正确的标签。这里先尝试一种常见方式：找第一个包含"/drug/"的链接
#     first_link = None
#     # 方法1：查找所有a标签，找href里包含"/drug/"的
#     all_links = search_soup.find_all('a', href=True)
#     for link in all_links:
#         if '/drug/' in link['href']:
#             first_link = link['href']
#             print(f"找到药品链接: {first_link}")
#             break
#
#     if not first_link:
#         print("未在搜索页找到药品链接")
#         return
#
#     # 拼接完整的URL（如果链接是相对的）
#     if first_link.startswith('http'):
#         drug_url = first_link
#     else:
#         drug_url = requests.compat.urljoin('https://www.dayi.org.cn', first_link)
#
#     # --- 第二步：进入药品详情页，提取内容 ---
#     print(f"\n2. 正在获取药品详情页: {drug_url}")
#     time.sleep(2)
#     drug_response = requests.get(drug_url, headers=headers)
#     drug_response.encoding = 'utf-8'
#
#     drug_soup = BeautifulSoup(drug_response.text, 'html.parser')
#
#     # 提取药品名称（通常在h1标签内）
#     name_tag = drug_soup.find('h1')
#     drug_name = name_tag.get_text(strip=True) if name_tag else "未找到名称"
#
#     # 提取所有正文内容（这里简单提取所有<p>标签的文本，你可以根据需要调整）
#     print("\n3. 提取的药品说明内容:")
#     print(f"【药品名称】{drug_name}")
#     print("\n【详细说明】")
#
#     # 找到通常存放内容的主体区域（根据你提供的详情页，内容在h1下面的各级标题和段落里）
#     # 简单方法：提取页面中所有段落，过滤掉太短的（可能是导航栏）
#     paragraphs = drug_soup.find_all('p')
#     content_lines = []
#     for p in paragraphs:
#         text = p.get_text(strip=True)
#         # 只保留有一定长度的文本，排除“关于我们”等导航栏的短文本
#         if text and len(text) > 10:
#             content_lines.append(text)
#
#     # 打印所有内容段落
#     for line in content_lines:
#         print(line)
#
#     # 可选：如果你想提取更结构化的信息（如成分、功效等），可以针对特定标题后的内容进行提取
#     # 但这会让代码变复杂，先实现最简单的版本。
#
# # 使用示例
# if __name__ == "__main__":
#     # 直接用你提供的搜索URL
#     search_url = "https://www.dayi.org.cn/search?keyword=阿莫西林&type=medical"
#     get_first_drug_info(search_url)
#
"""dddd"""
import requests
from bs4 import BeautifulSoup
import time
#
#
# def get_first_drug_info(search_url):
#     """
#     从搜索URL获取第一条药品链接，并打印其详情页内容
#     """
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#     }
#
#     # --- 第一步：处理搜索页，获取第一条药品详情页的链接 ---
#     print("1. 正在获取搜索页...")
#     search_response = requests.get(search_url, headers=headers)
#     search_response.encoding = 'utf-8'
#     search_soup = BeautifulSoup(search_response.text, 'html.parser')
#
#     # 找到第一个药品详情页的链接
#     first_link = None
#     all_links = search_soup.find_all('a', href=True)
#     for link in all_links:
#         if '/drug/' in link['href']:
#             first_link = link['href']
#             print(f"找到药品链接: {first_link}")
#             break
#
#     if not first_link:
#         print("未在搜索页找到药品链接")
#         return
#
#     # 拼接完整的URL
#     if first_link.startswith('http'):
#         drug_url = first_link
#     else:
#         drug_url = requests.compat.urljoin('https://www.dayi.org.cn', first_link)
#
#     # --- 第二步：进入药品详情页，提取内容 ---
#     print(f"\n2. 正在获取药品详情页: {drug_url}")
#     time.sleep(2)
#     drug_response = requests.get(drug_url, headers=headers)
#     drug_response.encoding = 'utf-8'
#     # print(drug_response.text)
#
#     drug_soup = BeautifulSoup(drug_response.text, 'html.parser')
#
#     # 提取药品名称
#     name_tag = drug_soup.find('h1')
#     drug_name = name_tag.get_text(strip=True) if name_tag else "未找到名称"
#     print(f"\n3. 药品名称: {drug_name}\n")
#     print("4. 药品详细信息: \n")
#
#     # 方法1：按顺序提取所有标题和段落
#     # 找到主要内容区域（根据实际HTML结构，可能在某个特定的div内）
#     # 先尝试找到包含药品信息的容器，如果没有特定容器，就从body开始找
#     content_container = drug_soup.find('div', class_='content') or \
#                         drug_soup.find('div', class_='main-content') or \
#                         drug_soup.find('div', class_='drug-info') or \
#                         drug_soup.find('article') or \
#                         drug_soup.body
#
#     if content_container:
#         # 获取容器内的所有元素，按顺序处理
#         for element in content_container.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol']):
#             # 跳过顶层的h1（因为我们已经提取了药品名称）
#             if element.name == 'h1' and element == name_tag:
#                 continue
#
#             if element.name in ['h2', 'h3', 'h4']:
#                 # 这是标题
#                 title_text = element.get_text(strip=True)
#                 if title_text:  # 只输出非空标题
#                     print(f"\n【{title_text}】")
#
#                     # 硬判断：如果标题是"有效期"或"保质期"，使用专门方法提取
#                     if "有效期" in title_text or "保质期" in title_text:
#                         extract_expiry_info(element, drug_soup)
#
#             elif element.name == 'p':
#                 # 这是段落
#                 p_text = element.get_text(strip=True)
#                 # if p_text and len(p_text) > 10:  # 过滤太短的文本
#                 print(p_text)
#
#             # elif element.name in ['ul', 'ol']:
#             #     # 这是列表
#             #     for li in element.find_all('li', recursive=False):
#             #         li_text = li.get_text(strip=True)
#             #         if li_text:
#             #             print(f"  • {li_text}")
#     else:
#         print("未找到主要内容区域")
#
#     # # 打印所有找到的标题（用于调试）
#     # print(f"\n\n找到的标题列表：")
#     # headings = drug_soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
#     # for h in headings:
#     #     print(f"{h.name}: {h.get_text(strip=True)}")
#
#
# ########################################
#
# def extract_expiry_info(expiry_title_element, drug_soup):
#     """简化版：直接针对你看到的HTML结构"""
#
#     ytime_div = drug_soup.find('div', id='ytime')
#     if ytime_div:
#         # 找到field-container父级
#         container = ytime_div.find_parent('div', class_='field-container')
#         if container:
#             # 找field-content
#             field_content = container.find('div', class_='field-content')
#             if field_content:
#                 expiry_text = field_content.get_text(strip=True)
#                 print(f"\n{expiry_text}")
#                 return
#
# # 使用示例
# if __name__ == "__main__":
#     search_url = "https://www.dayi.org.cn/search?keyword=清开灵颗粒&type=medical"
#     get_first_drug_info(search_url)


def get_first_drug_info(search_url):
    """
    从搜索URL获取第一条药品链接，并返回包含药品名称和详细信息的字典
    返回格式: {'name': '药品名称', 'content': {'标题1': '段落1', '标题2': '段落2', ...}}
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # --- 第一步：处理搜索页，获取第一条药品详情页的链接 ---
    print("1. 正在获取搜索页...")
    search_response = requests.get(search_url, headers=headers)
    search_response.encoding = 'utf-8'
    search_soup = BeautifulSoup(search_response.text, 'html.parser')

    # 找到第一个药品详情页的链接
    first_link = None
    all_links = search_soup.find_all('a', href=True)
    for link in all_links:
        if '/drug/' in link['href']:
            first_link = link['href']
            print(f"找到药品链接: {first_link}")
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
    print(f"\n2. 正在获取药品详情页: {drug_url}")
    time.sleep(2)
    drug_response = requests.get(drug_url, headers=headers)
    drug_response.encoding = 'utf-8'

    drug_soup = BeautifulSoup(drug_response.text, 'html.parser')

    # 提取药品名称
    name_tag = drug_soup.find('h1')
    drug_name = name_tag.get_text(strip=True) if name_tag else "未找到名称"
    print(f"\n3. 药品名称: {drug_name}\n")

    info_dict = {}
    info_dict['name'] = drug_name

    print("4. 药品详细信息: \n")

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
            print(f"\n【介绍】")
            print(intro_text)

    # 提取六个基本属性（通用名称、汉语拼音等）
    # 找到所有short-field-item容器
    field_items = drug_soup.find_all('div', class_='short-field-item')
    if field_items:
        # 如果没有找到intro，才创建介绍标题
        if not intro_paragraph:
            print(f"\n【介绍】")

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
                    print(f"{title}：{content}")

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
                    print(f"\n【{current_title}】")

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
                        print(p_text)
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

    print(info_dict)
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
                print(f"{expiry_text}")
                return expiry_text
    return None

# 使用示例
if __name__ == "__main__":
    search_url = "https://www.dayi.org.cn/search?keyword=清开灵颗粒&type=medical"
    get_first_drug_info(search_url)
