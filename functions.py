import requests
from notion_client import Client
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

def load_config():
    try:
        if os.path.exists('notion.json'):
            with open('notion.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"读取配置文件失败：{e}")
    return None

def save_config(notion_key, database_id):
    try:
        config = {
            'notion_key': notion_key,
            'database_id': database_id
        }
        with open('notion.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置文件失败：{e}")

def perform_search(keyword):
    # 使用 Bangumi 的网页搜索接口
    api_url = "https://bgm.tv/subject_search/" + keyword
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    }
    params = {
        "cat": "2"  # 类型为动画
    }
    
    try:
        response = requests.get(api_url, headers=headers, params=params)
        response.encoding = "utf-8"  # 确保使用 UTF-8 编码
        
        if response.status_code != 200:
            print(f"搜索失败，状态码：{response.status_code}")
            print(f"错误信息：{response.text}")
            return None

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        items = soup.select("#browserItemList .item")
        
        for item in items:
            # 检查是否为动画类型
            type_icon = item.select_one(".ico_subject_type")
            if type_icon and "subject_type_2" in type_icon.get("class", []):
                title = item.select_one("h3 a").text.strip()
                name_cn = item.select_one(".info.tip").text.strip() if item.select_one(".info.tip") else ""
                id = item.select_one("h3 a")["href"].split("/")[-1]
                
                results.append({
                    "name": title,
                    "name_cn": name_cn,
                    "id": id
                })
        
        return results
        
    except requests.exceptions.RequestException as e:
        print(f"请求出错：{e}")
        return None
    except Exception as e:
        print(f"解析出错：{e}")
        return None

def get_bangumi_info(bangumi_id):
    # 取条目基本信息
    api_url = f"https://api.bgm.tv/v0/subjects/{bangumi_id}"
    persons_url = f"https://api.bgm.tv/v0/subjects/{bangumi_id}/persons"
    headers = {
        "User-Agent": "MyApp/1.0 (my-app@example.com)",
        "Accept": "application/json"
    }
    
    try:
        # 获取基本信息
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            print(f"请求失败，状态码：{response.status_code}")
            print(f"错误信息：{response.text}")
            return None

        data = response.json()

        # 获取人员信息
        persons_response = requests.get(persons_url, headers=headers)
        directors = []
        
        if persons_response.status_code == 200:
            persons_data = persons_response.json()
            # 从人员信息中筛选出导演
            for person in persons_data:
                if "职位" in person:
                    # 检查职位是否包含"导演"
                    if "导演" in person["职位"]:
                        directors.append(person.get("name", ""))
                    # 也可以检查是否"动画制作"或其相关职位
                    elif "动画制作" in person["职位"]:
                        directors.append(person.get("name", ""))

        # 提取所需字段
        return {
            'title': data.get("name", ""),
            'name_cn': data.get("name_cn", ""),
            'episodes': data.get("eps", 0),
            'air_date': data.get("date", ""),
            'rating_score': data.get("rating", {}).get("score", 0),
            'large': data.get("images", {}).get("large", ""),
            'common': data.get("images", {}).get("common", ""),
            'summary': data.get("summary", ""),
            'directors': ", ".join(directors) if directors else "未知"  # 新增导演字段
        }
        
    except requests.exceptions.RequestException as e:
        print(f"请求出错：{e}")
        return None
    except ValueError as e:
        print(f"解析JSON数据出错：{e}")
        return None

def notion_page_cheat(info, bangumi_id, notion, database_id):
    # 确保 bangumi_id 是字符串类型
    bangumi_id = str(bangumi_id)
    
    # 创建一个新的页面
    new_page = {
        "名称": {
            "title": [
                {
                    "text": {
                        "content": info['title']
                    }
                }
            ]
        },
        "中文名": {
            "rich_text": [
                {
                    "text": {
                        "content": info['name_cn']
                    }
                }
            ]
        },
        "话数": {
            "number": info['episodes']
        },
        "评分": {
            "number": info['rating_score']
        },
        "放送开始": {
            "date": {
                "start": info['air_date'] if info['air_date'] else None
            }
        },
        "ID": {
            "rich_text": [
                {
                    "text": {
                        "content": bangumi_id
                    }
                }
            ]
        },
        "链接": {
            "url": f"https://bangumi.tv/subject/{bangumi_id}"
        },
        "导演": {
            "rich_text": [
                {
                    "text": {
                        "content": info['directors']
                    }
                }
            ]
        }
    }

    # 只有在有效日期时才添加日期字段
    if info['air_date']:
        new_page["放送开始"] = {
            "date": {
                "start": info['air_date']
            }
        }

    # 定义页面正文内容（children）
    children = [
        {
            "object": "block",
            "type": "image",
            "image": {
                "type": "external",
                "external": {
                    "url": info['large']  # 图片的外部链接
                }
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "text": {
                            "content": "这是番剧的简介：" + info['summary']
                        }
                    }
                ]
            }
        }
    ]

    # 创建页面并添加正文内容
    response = notion.pages.create(
        parent={"database_id": database_id},
        properties=new_page,
        children=children  # 添加正文内容
    )

    print(f"已成功创建页面：{info['title']}")
    
    # 将番剧名称和ID保存到 anime.json 文件中
    try:
        anime_data = []
        # 检查文件是否存在且不为空
        if os.path.exists('anime.json') and os.path.getsize('anime.json') > 0:
            with open('anime.json', 'r', encoding='utf-8') as f:
                try:
                    anime_data = json.load(f)
                except json.JSONDecodeError:
                    print("anime.json 文件内容不是有效的 JSON，将重新创建文件。")
                    anime_data = []
        
        # 追加新数据
        anime_data.append({
            "title": info['title'],
            "id": bangumi_id
        })

        # 保存数据
        with open('anime.json', 'w', encoding='utf-8') as f:
            json.dump(anime_data, f, ensure_ascii=False, indent=2)
        
        print(f"已将番剧 {info['title']} 和 ID {bangumi_id} 保存到 anime.json 文件中")
    except Exception as e:
        print(f"保存番剧信息到 anime.json 文件失败：{e}")